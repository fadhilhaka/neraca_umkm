# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class NeracaWallet(models.Model):
    _name = "neraca.wallet"
    _description = "Dompet / Wallet"
    _order = "sequence, name"

    name = fields.Char(string="Nama Dompet", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        required=True,
        default=lambda self: self.env.ref("base.IDR", raise_if_not_found=False)
        or self.env.company.currency_id,
    )
    wallet_type = fields.Selection(
        [
            ("cash", "Tunai"),
            ("bank", "Bank"),
            ("ewallet", "E-Wallet"),
        ],
        string="Tipe Dompet",
        required=True,
        default="cash",
    )
    provider = fields.Selection(
        [
            ("kas_tunai", "Kas Tunai"),
            ("bca", "BCA"),
            ("mandiri", "Mandiri"),
            ("gopay", "GoPay"),
            ("ovo", "OVO"),
            ("dana", "Dana"),
            ("other", "Lainnya"),
        ],
        string="Provider",
        required=True,
        default="kas_tunai",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Jurnal",
        domain="[('type', 'in', ('cash', 'bank')), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Akun Likuiditas",
        related="journal_id.default_account_id",
        store=True,
        readonly=True,
    )
    balance = fields.Monetary(
        string="Saldo",
        compute="_compute_balance",
        currency_field="currency_id",
    )
    note = fields.Text(string="Catatan")

    _sql_constraints = [
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "Nama dompet harus unik per perusahaan.",
        ),
    ]

    @api.depends("journal_id", "journal_id.default_account_id")
    def _compute_balance(self):
        for wallet in self:
            if not wallet.journal_id or not wallet.journal_id.default_account_id:
                wallet.balance = 0.0
                continue
            account = wallet.journal_id.default_account_id
            # Prefer journal's reported balance when available
            if hasattr(wallet.journal_id, "current_statement_balance"):
                wallet.balance = wallet.journal_id.current_statement_balance or 0.0
            else:
                domain = [
                    ("account_id", "=", account.id),
                    ("parent_state", "=", "posted"),
                    ("company_id", "=", wallet.company_id.id),
                ]
                groups = self.env["account.move.line"].read_group(
                    domain, ["balance:sum"], []
                )
                wallet.balance = groups[0].get("balance", 0.0) if groups else 0.0

    def _provider_journal_type(self):
        self.ensure_one()
        if self.wallet_type == "cash" or self.provider == "kas_tunai":
            return "cash"
        return "bank"

    def _ensure_liquidity_account(self, journal_type):
        """Find or create a liquidity account for the wallet journal."""
        self.ensure_one()
        Account = self.env["account.account"]
        code_prefix = "1011" if journal_type == "cash" else "1012"
        existing = Account.search(
            [
                ("company_ids", "in", self.company_id.id),
                ("account_type", "=", "asset_cash"),
                ("code", "=like", f"{code_prefix}%"),
            ],
            limit=1,
        )
        if existing:
            return existing
        # Fallback: any cash account
        existing = Account.search(
            [
                ("company_ids", "in", self.company_id.id),
                ("account_type", "=", "asset_cash"),
            ],
            limit=1,
        )
        if existing:
            return existing
        # Create a simple liquidity account (Odoo 18 uses company_ids)
        code = f"{code_prefix}{self.id or self.env['ir.sequence'].next_by_code('neraca.wallet') or '00'}"
        return Account.create(
            {
                "name": _("Likuiditas %s") % self.name,
                "code": code[:64],
                "account_type": "asset_cash",
                "reconcile": False,
                "company_ids": [(6, 0, [self.company_id.id])],
            }
        )

    def _create_journal_for_wallet(self):
        self.ensure_one()
        if self.journal_id:
            return self.journal_id
        journal_type = self._provider_journal_type()
        account = self._ensure_liquidity_account(journal_type)
        Journal = self.env["account.journal"]
        code = (self.provider or "WAL")[:4].upper()
        # Ensure unique journal code
        base_code = code
        idx = 1
        while Journal.search(
            [("code", "=", code), ("company_id", "=", self.company_id.id)], limit=1
        ):
            code = f"{base_code}{idx}"[:5]
            idx += 1
        journal = Journal.create(
            {
                "name": self.name,
                "code": code,
                "type": journal_type,
                "company_id": self.company_id.id,
                "currency_id": self.currency_id.id,
                "default_account_id": account.id,
            }
        )
        return journal

    @api.model_create_multi
    def create(self, vals_list):
        wallets = super().create(vals_list)
        for wallet in wallets:
            if not wallet.journal_id:
                journal = wallet._create_journal_for_wallet()
                wallet.journal_id = journal.id
        return wallets

    def action_open_journal(self):
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_("Dompet belum memiliki jurnal."))
        return {
            "type": "ir.actions.act_window",
            "name": self.journal_id.display_name,
            "res_model": "account.journal",
            "view_mode": "form",
            "res_id": self.journal_id.id,
        }
