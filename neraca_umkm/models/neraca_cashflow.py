# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class NeracaCashflowHelper(models.AbstractModel):
    _name = "neraca.cashflow"
    _description = "Cashflow Board Data Helper"

    @api.model
    def _month_bounds(self, ref_date=None):
        today = ref_date or fields.Date.context_today(self)
        start = today.replace(day=1)
        end = start + relativedelta(months=1, days=-1)
        return start, end, today

    @api.model
    def _liquidity_account_ids(self, company):
        wallets = self.env["neraca.wallet"].search([("company_id", "=", company.id)])
        accounts = wallets.mapped("journal_id.default_account_id")
        if not accounts:
            accounts = self.env["account.account"].search(
                [
                    ("company_ids", "in", company.id),
                    ("account_type", "=", "asset_cash"),
                ]
            )
        return accounts.ids

    @api.model
    def _sum_liquidity_moves(self, company, date_from, date_to, direction):
        """Sum cash inflows (credit) or outflows (debit) on liquidity accounts."""
        account_ids = self._liquidity_account_ids(company)
        if not account_ids:
            return 0.0
        domain = [
            ("account_id", "in", account_ids),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        MoveLine = self.env["account.move.line"]
        if direction == "in":
            domain.append(("credit", ">", 0))
            groups = MoveLine.read_group(domain, ["credit:sum"], [])
            return groups[0].get("credit", 0.0) if groups else 0.0
        domain.append(("debit", ">", 0))
        groups = MoveLine.read_group(domain, ["debit:sum"], [])
        return groups[0].get("debit", 0.0) if groups else 0.0

    @api.model
    def _wallet_total_balance(self, company):
        wallets = self.env["neraca.wallet"].search([("company_id", "=", company.id)])
        return sum(wallets.mapped("balance"))

    @api.model
    def _budget_planned_expense(self, company, date_from, date_to):
        budgets = self.env["neraca.budget"].search(
            [
                ("company_id", "=", company.id),
                ("state", "in", ("confirmed", "done")),
                ("date_start", "<=", date_to),
                ("date_end", ">=", date_from),
            ]
        )
        return sum(budgets.mapped("amount_planned"))

    @api.model
    def _avg_daily_net(self, company, days=30):
        today = fields.Date.context_today(self)
        start = today - timedelta(days=days)
        inflow = self._sum_liquidity_moves(company, start, today, "in")
        outflow = self._sum_liquidity_moves(company, start, today, "out")
        return (inflow - outflow) / float(days or 1)

    @api.model
    def get_dashboard_data(self):
        """JSON payload for the OWL cashflow dashboard."""
        company = self.env.company
        currency = company.currency_id
        start, end, today = self._month_bounds()

        inflow = self._sum_liquidity_moves(company, start, end, "in")
        outflow = self._sum_liquidity_moves(company, start, end, "out")
        net = inflow - outflow
        balance = self._wallet_total_balance(company)

        avg_daily_out = abs(
            min(self._avg_daily_net(company, 30), 0.0)
        ) or (outflow / max((today - start).days, 1))
        runway_days = int(balance / avg_daily_out) if avg_daily_out else None

        planned = self._budget_planned_expense(company, start, end)
        avg_net = self._avg_daily_net(company, 30)

        def project(days):
            # Prefer budget remaining + recent average net
            remaining_budget = max(planned - outflow, 0.0)
            budget_share = remaining_budget * (days / 30.0) if planned else 0.0
            avg_projection = avg_net * days
            # Blend: if budget exists weight it, else pure average
            if planned:
                projected_net = avg_projection * 0.4 - budget_share * 0.6 / max(days / 30.0, 0.1) * (days / 30.0)
                # Simpler: balance + avg_net*days - remaining budget portion
                return balance + avg_net * days - (remaining_budget * (days / 30.0) * 0.5)
            return balance + avg_net * days

        wallets = self.env["neraca.wallet"].search(
            [("company_id", "=", company.id)], order="sequence, name"
        )
        wallet_rows = [
            {
                "id": w.id,
                "name": w.name,
                "type": w.wallet_type,
                "provider": w.provider,
                "balance": w.balance,
            }
            for w in wallets
        ]

        return {
            "company": company.name,
            "currency": {
                "name": currency.name,
                "symbol": currency.symbol,
                "position": currency.position,
                "decimal_places": currency.decimal_places,
            },
            "period": {
                "start": fields.Date.to_string(start),
                "end": fields.Date.to_string(end),
                "today": fields.Date.to_string(today),
            },
            "inflow": inflow,
            "outflow": outflow,
            "net": net,
            "balance": balance,
            "runway_days": runway_days,
            "projections": {
                "d30": project(30),
                "d60": project(60),
                "d90": project(90),
            },
            "budget_planned": planned,
            "wallets": wallet_rows,
        }
