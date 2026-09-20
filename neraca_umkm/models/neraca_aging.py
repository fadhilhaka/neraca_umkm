# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class NeracaPartnerAging(models.TransientModel):
    _name = "neraca.partner.aging"
    _description = "Piutang & Utang Lite"
    _order = "date_maturity asc, residual desc"

    partner_id = fields.Many2one("res.partner", string="Mitra", required=True)
    move_id = fields.Many2one("account.move", string="Dokumen")
    move_line_id = fields.Many2one("account.move.line", string="Baris Jurnal")
    name = fields.Char(string="Referensi")
    date = fields.Date(string="Tanggal")
    date_maturity = fields.Date(string="Jatuh Tempo")
    aging_type = fields.Selection(
        [
            ("receivable", "Piutang"),
            ("payable", "Utang"),
        ],
        string="Tipe",
        required=True,
    )
    residual = fields.Monetary(string="Sisa", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="Mata Uang")
    company_id = fields.Many2one("res.company", string="Perusahaan")
    days_overdue = fields.Integer(string="Hari Terlambat", compute="_compute_days_overdue")

    @api.depends("date_maturity")
    def _compute_days_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.date_maturity and rec.date_maturity < today:
                rec.days_overdue = (today - rec.date_maturity).days
            else:
                rec.days_overdue = 0

    @api.model
    def _prepare_aging_lines(self, aging_type="receivable"):
        """Build transient rows from open receivable/payable move lines."""
        company = self.env.company
        account_type = (
            "asset_receivable" if aging_type == "receivable" else "liability_payable"
        )
        domain = [
            ("account_id.account_type", "=", account_type),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("company_id", "=", company.id),
            ("amount_residual", "!=", 0),
        ]
        lines = self.env["account.move.line"].search(domain, order="date_maturity asc")
        vals_list = []
        for line in lines:
            residual = line.amount_residual
            if aging_type == "payable":
                residual = -residual  # show positive utang amount
            vals_list.append(
                {
                    "partner_id": line.partner_id.id or False,
                    "move_id": line.move_id.id,
                    "move_line_id": line.id,
                    "name": line.move_id.name or line.name or "",
                    "date": line.date,
                    "date_maturity": line.date_maturity or line.date,
                    "aging_type": aging_type,
                    "residual": residual,
                    "currency_id": (line.currency_id or company.currency_id).id,
                    "company_id": company.id,
                }
            )
        return vals_list

    @api.model
    def action_open_piutang(self):
        self.search([("aging_type", "=", "receivable")]).unlink()
        vals = self._prepare_aging_lines("receivable")
        records = self.create(vals) if vals else self.browse()
        return {
            "type": "ir.actions.act_window",
            "name": _("Piutang"),
            "res_model": "neraca.partner.aging",
            "view_mode": "list,form",
            "domain": [("aging_type", "=", "receivable"), ("id", "in", records.ids)],
            "context": {"default_aging_type": "receivable"},
            "target": "current",
        }

    @api.model
    def action_open_utang(self):
        self.search([("aging_type", "=", "payable")]).unlink()
        vals = self._prepare_aging_lines("payable")
        records = self.create(vals) if vals else self.browse()
        return {
            "type": "ir.actions.act_window",
            "name": _("Utang"),
            "res_model": "neraca.partner.aging",
            "view_mode": "list,form",
            "domain": [("aging_type", "=", "payable"), ("id", "in", records.ids)],
            "context": {"default_aging_type": "payable"},
            "target": "current",
        }
