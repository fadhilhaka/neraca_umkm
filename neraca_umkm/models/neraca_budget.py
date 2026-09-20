# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class NeracaBudget(models.Model):
    _name = "neraca.budget"
    _description = "Anggaran Bulanan"
    _order = "date_start desc, name"

    name = fields.Char(string="Nama Anggaran", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date_start = fields.Date(string="Mulai", required=True)
    date_end = fields.Date(string="Selesai", required=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Dikonfirmasi"),
            ("done", "Selesai"),
            ("cancelled", "Dibatalkan"),
        ],
        string="Status",
        default="draft",
        required=True,
    )
    line_ids = fields.One2many(
        "neraca.budget.line",
        "budget_id",
        string="Baris Anggaran",
        copy=True,
    )
    amount_planned = fields.Monetary(
        string="Total Rencana",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_actual = fields.Monetary(
        string="Total Aktual",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_variance = fields.Monetary(
        string="Selisih",
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    is_over_budget = fields.Boolean(
        string="Melebihi Anggaran",
        compute="_compute_amounts",
        store=True,
    )
    note = fields.Text(string="Catatan")

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("Tanggal mulai harus sebelum tanggal selesai."))

    @api.depends(
        "line_ids.amount_planned",
        "line_ids.amount_actual",
        "line_ids.amount_variance",
    )
    def _compute_amounts(self):
        for budget in self:
            planned = sum(budget.line_ids.mapped("amount_planned"))
            actual = sum(budget.line_ids.mapped("amount_actual"))
            budget.amount_planned = planned
            budget.amount_actual = actual
            budget.amount_variance = planned - actual
            budget.is_over_budget = actual > planned and planned > 0

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_draft(self):
        self.write({"state": "draft"})

    def action_recompute_actuals(self):
        self.line_ids._compute_actual()
        self._compute_amounts()
        return True

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        today = fields.Date.context_today(self)
        start = today.replace(day=1)
        end = start + relativedelta(months=1, days=-1)
        res.setdefault("date_start", start)
        res.setdefault("date_end", end)
        res.setdefault("name", _("Anggaran %s") % start.strftime("%B %Y"))
        return res



    @api.model
    def load_demo_budget_lines(self, budget_ids):
        """Called from demo XML to attach sample expense lines when CoA exists."""
        budgets = self.browse(budget_ids)
        Account = self.env["account.account"]
        for budget in budgets:
            if budget.line_ids:
                continue
            accounts = Account.search(
                [
                    ("account_type", "in", ("expense", "expense_direct_cost")),
                    ("company_ids", "in", budget.company_id.id),
                ],
                limit=5,
            )
            if not accounts:
                continue
            templates = [
                ("Sewa kios", 2500000.0, 10),
                ("Listrik & air", 500000.0, 20),
                ("Belanja barang dagangan", 8000000.0, 30),
            ]
            vals = []
            for idx, (name, amount, seq) in enumerate(templates):
                account = accounts[idx % len(accounts)]
                vals.append(
                    {
                        "budget_id": budget.id,
                        "name": name,
                        "account_id": account.id,
                        "amount_planned": amount,
                        "sequence": seq,
                    }
                )
            self.env["neraca.budget.line"].create(vals)
        return True

class NeracaBudgetLine(models.Model):
    _name = "neraca.budget.line"
    _description = "Baris Anggaran"
    _order = "budget_id, sequence, id"

    budget_id = fields.Many2one(
        "neraca.budget",
        string="Anggaran",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Keterangan")
    account_id = fields.Many2one(
        "account.account",
        string="Akun Beban",
        required=True,
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost', 'expense_depreciation'))]",
    )
    company_id = fields.Many2one(related="budget_id.company_id", store=True)
    currency_id = fields.Many2one(related="budget_id.currency_id")
    amount_planned = fields.Monetary(
        string="Rencana",
        required=True,
        currency_field="currency_id",
        default=0.0,
    )
    amount_actual = fields.Monetary(
        string="Aktual",
        compute="_compute_actual",
        currency_field="currency_id",
        store=True,
    )
    amount_variance = fields.Monetary(
        string="Selisih",
        compute="_compute_actual",
        currency_field="currency_id",
        store=True,
    )
    variance_percent = fields.Float(
        string="% Selisih",
        compute="_compute_actual",
        store=True,
    )
    is_over_budget = fields.Boolean(
        string="Melebihi",
        compute="_compute_actual",
        store=True,
    )

    @api.depends(
        "account_id",
        "amount_planned",
        "budget_id.date_start",
        "budget_id.date_end",
        "budget_id.company_id",
    )
    def _compute_actual(self):
        MoveLine = self.env["account.move.line"]
        for line in self:
            if not line.account_id or not line.budget_id.date_start:
                line.amount_actual = 0.0
                line.amount_variance = line.amount_planned
                line.variance_percent = 0.0
                line.is_over_budget = False
                continue
            domain = [
                ("account_id", "=", line.account_id.id),
                ("parent_state", "=", "posted"),
                ("company_id", "=", line.company_id.id),
                ("date", ">=", line.budget_id.date_start),
                ("date", "<=", line.budget_id.date_end),
            ]
            groups = MoveLine.read_group(domain, ["balance:sum"], [])
            # Expense accounts: debit increases expense → positive balance
            balance = groups[0].get("balance", 0.0) if groups else 0.0
            actual = abs(balance)
            line.amount_actual = actual
            line.amount_variance = line.amount_planned - actual
            if line.amount_planned:
                line.variance_percent = (line.amount_variance / line.amount_planned) * 100.0
            else:
                line.variance_percent = 0.0
            line.is_over_budget = actual > line.amount_planned and line.amount_planned > 0
