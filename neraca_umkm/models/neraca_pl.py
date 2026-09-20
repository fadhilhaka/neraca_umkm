# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class NeracaPLReport(models.TransientModel):
    _name = "neraca.pl.report"
    _description = "Laporan Laba Rugi UMKM"

    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    period_type = fields.Selection(
        [
            ("month", "Bulan Ini"),
            ("ytd", "Tahun Berjalan (YTD)"),
        ],
        string="Periode",
        default="month",
        required=True,
    )
    date_from = fields.Date(string="Dari")
    date_to = fields.Date(string="Sampai")
    amount_income = fields.Monetary(
        string="Pendapatan",
        currency_field="currency_id",
        readonly=True,
    )
    amount_expense = fields.Monetary(
        string="Beban",
        currency_field="currency_id",
        readonly=True,
    )
    amount_net = fields.Monetary(
        string="Laba / Rugi Bersih",
        currency_field="currency_id",
        readonly=True,
    )
    line_ids = fields.One2many(
        "neraca.pl.report.line",
        "report_id",
        string="Rincian",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        start = today.replace(day=1)
        end = start + relativedelta(months=1, days=-1)
        res.setdefault("date_from", start)
        res.setdefault("date_to", end)
        res.setdefault("period_type", "month")
        return res

    @api.onchange("period_type")
    def _onchange_period_type(self):
        today = fields.Date.context_today(self)
        if self.period_type == "ytd":
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today
        else:
            start = today.replace(day=1)
            self.date_from = start
            self.date_to = start + relativedelta(months=1, days=-1)

    def _income_account_types(self):
        return ("income", "income_other")

    def _expense_account_types(self):
        return ("expense", "expense_direct_cost", "expense_depreciation")

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        MoveLine = self.env["account.move.line"]
        company = self.company_id
        date_from = self.date_from
        date_to = self.date_to

        def account_sums(account_types):
            domain = [
                ("account_id.account_type", "in", account_types),
                ("parent_state", "=", "posted"),
                ("company_id", "=", company.id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
            return MoveLine.read_group(
                domain,
                ["balance:sum", "account_id"],
                ["account_id"],
            )

        income_groups = account_sums(self._income_account_types())
        expense_groups = account_sums(self._expense_account_types())

        line_vals = []
        total_income = 0.0
        for g in income_groups:
            # Income: credit → negative balance in Odoo; show as positive income
            bal = -(g.get("balance") or 0.0)
            if not bal:
                continue
            total_income += bal
            line_vals.append(
                {
                    "report_id": self.id,
                    "section": "income",
                    "account_id": g["account_id"][0],
                    "amount": bal,
                }
            )

        total_expense = 0.0
        for g in expense_groups:
            bal = g.get("balance") or 0.0
            if not bal:
                continue
            amount = abs(bal)
            total_expense += amount
            line_vals.append(
                {
                    "report_id": self.id,
                    "section": "expense",
                    "account_id": g["account_id"][0],
                    "amount": amount,
                }
            )

        if line_vals:
            self.env["neraca.pl.report.line"].create(line_vals)

        self.write(
            {
                "amount_income": total_income,
                "amount_expense": total_expense,
                "amount_net": total_income - total_expense,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "neraca.pl.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    @api.model
    def action_open_pl(self):
        wizard = self.create({})
        wizard.action_compute()
        return {
            "type": "ir.actions.act_window",
            "name": _("Laporan Laba Rugi UMKM"),
            "res_model": "neraca.pl.report",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "current",
        }


class NeracaPLReportLine(models.TransientModel):
    _name = "neraca.pl.report.line"
    _description = "Baris Laba Rugi UMKM"
    _order = "section, account_id"

    report_id = fields.Many2one(
        "neraca.pl.report",
        required=True,
        ondelete="cascade",
    )
    section = fields.Selection(
        [
            ("income", "Pendapatan"),
            ("expense", "Beban"),
        ],
        string="Bagian",
        required=True,
    )
    account_id = fields.Many2one("account.account", string="Akun")
    amount = fields.Monetary(string="Jumlah", currency_field="currency_id")
    currency_id = fields.Many2one(related="report_id.currency_id")
