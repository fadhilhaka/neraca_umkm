# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class NeracaCategoryReport(models.TransientModel):
    _name = "neraca.category.report"
    _description = "Laporan Per Kategori"

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
            ("custom", "Kustom"),
        ],
        string="Periode",
        default="month",
        required=True,
    )
    date_from = fields.Date(string="Dari")
    date_to = fields.Date(string="Sampai")
    amount_income = fields.Monetary(
        string="Total Pendapatan",
        currency_field="currency_id",
        readonly=True,
    )
    amount_expense = fields.Monetary(
        string="Total Beban",
        currency_field="currency_id",
        readonly=True,
    )
    amount_net = fields.Monetary(
        string="Bersih",
        currency_field="currency_id",
        readonly=True,
    )
    line_ids = fields.One2many(
        "neraca.category.report.line",
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
        elif self.period_type == "month":
            start = today.replace(day=1)
            self.date_from = start
            self.date_to = start + relativedelta(months=1, days=-1)

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        MoveLine = self.env["account.move.line"]
        Category = self.env["neraca.category"]
        company = self.company_id
        date_from = self.date_from
        date_to = self.date_to

        # Prefer AML tagged with neraca_category_id
        tagged_domain = [
            ("neraca_category_id", "!=", False),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        tagged_groups = MoveLine.read_group(
            tagged_domain,
            ["balance:sum", "neraca_category_id"],
            ["neraca_category_id"],
        )

        line_vals = []
        total_income = 0.0
        total_expense = 0.0
        for g in tagged_groups:
            cat_data = g.get("neraca_category_id")
            if not cat_data:
                continue
            cat_id = cat_data[0]
            cat = Category.browse(cat_id)
            bal = g.get("balance") or 0.0
            if cat.category_type == "income":
                amount = abs(bal) if bal else 0.0
                # Income credits → negative balance; normalize to positive
                if bal < 0:
                    amount = -bal
                else:
                    amount = abs(bal)
                section = "income"
                total_income += amount
            else:
                amount = abs(bal)
                section = "expense"
                total_expense += amount
            if not amount:
                continue
            line_vals.append(
                {
                    "report_id": self.id,
                    "section": section,
                    "category_id": cat_id,
                    "amount": amount,
                    "color": cat.color or False,
                }
            )

        # Fallback: group untagged P&L lines by account type into synthetic buckets
        untagged_domain = [
            ("neraca_category_id", "=", False),
            ("parent_state", "=", "posted"),
            ("company_id", "=", company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            (
                "account_id.account_type",
                "in",
                (
                    "income",
                    "income_other",
                    "expense",
                    "expense_direct_cost",
                    "expense_depreciation",
                ),
            ),
        ]
        untagged_groups = MoveLine.read_group(
            untagged_domain,
            ["balance:sum", "account_id"],
            ["account_id"],
        )

        fallback_income = 0.0
        fallback_expense = 0.0
        Account = self.env["account.account"]
        income_types = ("income", "income_other")
        for g in untagged_groups:
            acc_data = g.get("account_id")
            if not acc_data:
                continue
            bal = g.get("balance") or 0.0
            if not bal:
                continue
            atype = Account.browse(acc_data[0]).account_type
            if atype in income_types:
                amount = -bal if bal < 0 else abs(bal)
                fallback_income += amount
            else:
                amount = abs(bal)
                fallback_expense += amount

        if fallback_income:
            line_vals.append(
                {
                    "report_id": self.id,
                    "section": "income",
                    "category_id": False,
                    "name_fallback": _("Lainnya (tanpa kategori)"),
                    "amount": fallback_income,
                    "color": "#9CA3AF",
                }
            )
            total_income += fallback_income
        if fallback_expense:
            line_vals.append(
                {
                    "report_id": self.id,
                    "section": "expense",
                    "category_id": False,
                    "name_fallback": _("Lainnya (tanpa kategori)"),
                    "amount": fallback_expense,
                    "color": "#9CA3AF",
                }
            )
            total_expense += fallback_expense

        if line_vals:
            self.env["neraca.category.report.line"].create(line_vals)

        self.write(
            {
                "amount_income": total_income,
                "amount_expense": total_expense,
                "amount_net": total_income - total_expense,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "neraca.category.report",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    @api.model
    def action_open_report(self):
        wizard = self.create({})
        wizard.action_compute()
        return {
            "type": "ir.actions.act_window",
            "name": _("Laporan Per Kategori"),
            "res_model": "neraca.category.report",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "current",
        }


class NeracaCategoryReportLine(models.TransientModel):
    _name = "neraca.category.report.line"
    _description = "Baris Laporan Per Kategori"
    _order = "section, amount desc, id"

    report_id = fields.Many2one(
        "neraca.category.report",
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
    category_id = fields.Many2one("neraca.category", string="Kategori")
    name_fallback = fields.Char(string="Label")
    display_name_cat = fields.Char(
        string="Nama",
        compute="_compute_display_name_cat",
    )
    amount = fields.Monetary(string="Jumlah", currency_field="currency_id")
    currency_id = fields.Many2one(related="report_id.currency_id")
    color = fields.Char(string="Warna")

    @api.depends("category_id", "name_fallback")
    def _compute_display_name_cat(self):
        for line in self:
            line.display_name_cat = (
                line.category_id.name if line.category_id else (line.name_fallback or "")
            )
