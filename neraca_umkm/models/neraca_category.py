# -*- coding: utf-8 -*-
from odoo import api, fields, models


class NeracaCategory(models.Model):
    _name = "neraca.category"
    _description = "Kategori Transaksi UMKM"
    _order = "sequence, name"

    name = fields.Char(string="Nama Kategori", required=True, translate=True)
    category_type = fields.Selection(
        [
            ("income", "Pendapatan"),
            ("expense", "Beban"),
        ],
        string="Tipe",
        required=True,
        default="expense",
    )
    color = fields.Char(
        string="Warna",
        help="Kode warna hex, contoh #CE3C2B",
        default="#6B7280",
    )
    icon = fields.Char(string="Ikon", help="Opsional: nama ikon / emoji")
    account_id = fields.Many2one(
        "account.account",
        string="Akun Akuntansi",
        domain=[
            (
                "account_type",
                "in",
                (
                    "income",
                    "income_other",
                    "expense",
                    "expense_direct_cost",
                    "expense_depreciation",
                ),
            )
        ],
        ondelete="set null",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _sql_constraints = [
        (
            "name_type_company_uniq",
            "unique(name, category_type, company_id)",
            "Nama kategori harus unik per tipe dan perusahaan.",
        ),
    ]
