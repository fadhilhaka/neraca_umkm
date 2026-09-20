# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    neraca_category_id = fields.Many2one(
        "neraca.category",
        string="Kategori Neraca",
        index=True,
        ondelete="set null",
        help="Kategori UMKM untuk laporan cashflow & per kategori.",
    )
