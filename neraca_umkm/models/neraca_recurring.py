# -*- coding: utf-8 -*-
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NeracaRecurring(models.Model):
    _name = "neraca.recurring"
    _description = "Transaksi Berulang"
    _order = "next_date, name"

    name = fields.Char(string="Nama", required=True)
    recurring_type = fields.Selection(
        [
            ("in", "Masuk"),
            ("out", "Keluar"),
        ],
        string="Arah",
        required=True,
        default="out",
    )
    amount = fields.Monetary(
        string="Jumlah",
        required=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        required=True,
        default=lambda self: self.env.ref("base.IDR", raise_if_not_found=False)
        or self.env.company.currency_id,
    )
    wallet_id = fields.Many2one(
        "neraca.wallet",
        string="Dompet",
        required=True,
        ondelete="restrict",
        domain="[('company_id', '=', company_id)]",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Jurnal",
        related="wallet_id.journal_id",
        store=True,
        readonly=True,
    )
    category_id = fields.Many2one(
        "neraca.category",
        string="Kategori",
        ondelete="set null",
        domain="[('company_id', '=', company_id)]",
    )
    partner_id = fields.Many2one("res.partner", string="Mitra")
    frequency = fields.Selection(
        [
            ("daily", "Harian"),
            ("weekly", "Mingguan"),
            ("monthly", "Bulanan"),
            ("yearly", "Tahunan"),
        ],
        string="Frekuensi",
        required=True,
        default="monthly",
    )
    interval = fields.Integer(
        string="Interval",
        default=1,
        required=True,
        help="Setiap N hari/minggu/bulan/tahun.",
    )
    next_date = fields.Date(
        string="Tanggal Berikutnya",
        required=True,
        default=fields.Date.context_today,
    )
    day_of_month = fields.Integer(
        string="Hari dalam Bulan",
        help="Untuk frekuensi bulanan: hari target (1–28). 0 = gunakan next_date.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    last_run_date = fields.Date(string="Terakhir Dijalankan", readonly=True)
    notes = fields.Text(string="Catatan")
    run_ids = fields.One2many(
        "neraca.recurring.run",
        "recurring_id",
        string="Log Eksekusi",
    )

    @api.constrains("interval", "amount", "day_of_month")
    def _check_positive(self):
        for rec in self:
            if rec.interval < 1:
                raise UserError(_("Interval harus minimal 1."))
            if rec.amount <= 0:
                raise UserError(_("Jumlah harus lebih dari nol."))
            if rec.day_of_month and (rec.day_of_month < 1 or rec.day_of_month > 28):
                raise UserError(_("Hari dalam bulan harus antara 1 dan 28."))

    def _advance_next_date(self, from_date=None):
        """Compute the next occurrence after from_date (default: current next_date)."""
        self.ensure_one()
        base = from_date or self.next_date
        interval = self.interval or 1
        if self.frequency == "daily":
            nxt = base + timedelta(days=interval)
        elif self.frequency == "weekly":
            nxt = base + timedelta(weeks=interval)
        elif self.frequency == "yearly":
            nxt = base + relativedelta(years=interval)
        else:
            # monthly
            nxt = base + relativedelta(months=interval)
            if self.day_of_month:
                try:
                    nxt = nxt.replace(day=self.day_of_month)
                except ValueError:
                    # clamp to last day of month
                    nxt = nxt + relativedelta(day=31)
        return nxt

    def _counterpart_account(self):
        """Pick income/expense account from category or CoA fallback."""
        self.ensure_one()
        if self.category_id and self.category_id.account_id:
            return self.category_id.account_id
        Account = self.env["account.account"]
        if self.recurring_type == "in":
            types = ("income", "income_other")
        else:
            types = ("expense", "expense_direct_cost")
        account = Account.search(
            [
                ("account_type", "in", types),
                ("company_ids", "in", self.company_id.id),
            ],
            limit=1,
        )
        if not account:
            raise UserError(
                _("Tidak menemukan akun lawan untuk transaksi berulang '%s'. "
                  "Hubungkan kategori ke akun, atau pastikan Chart of Accounts terpasang.")
                % self.name
            )
        return account

    def _generate_move(self, run_date=None):
        """Create and post an account.move for this recurring item.

        Idempotent: skips if a run log already exists for (recurring, run_date).
        """
        self.ensure_one()
        run_date = run_date or self.next_date or fields.Date.context_today(self)
        Run = self.env["neraca.recurring.run"]
        existing = Run.search(
            [
                ("recurring_id", "=", self.id),
                ("run_date", "=", run_date),
            ],
            limit=1,
        )
        if existing:
            return existing.move_id

        if not self.wallet_id or not self.wallet_id.journal_id:
            raise UserError(
                _("Dompet '%s' belum memiliki jurnal.") % (self.wallet_id.name or "")
            )
        journal = self.wallet_id.journal_id
        liquidity = journal.default_account_id
        if not liquidity:
            raise UserError(
                _("Jurnal '%s' belum punya akun likuiditas default.") % journal.display_name
            )
        counterpart = self._counterpart_account()
        amount = self.amount

        # out: debit expense, credit liquidity; in: debit liquidity, credit income
        if self.recurring_type == "out":
            liq_debit, liq_credit = 0.0, amount
            cp_debit, cp_credit = amount, 0.0
        else:
            liq_debit, liq_credit = amount, 0.0
            cp_debit, cp_credit = 0.0, amount

        line_liquidity = {
            "name": self.name,
            "account_id": liquidity.id,
            "debit": liq_debit,
            "credit": liq_credit,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "neraca_category_id": self.category_id.id if self.category_id else False,
        }
        line_counterpart = {
            "name": self.name,
            "account_id": counterpart.id,
            "debit": cp_debit,
            "credit": cp_credit,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "neraca_category_id": self.category_id.id if self.category_id else False,
        }

        move = self.env["account.move"].create(
            {
                "journal_id": journal.id,
                "date": run_date,
                "ref": _("Berulang: %s") % self.name,
                "company_id": self.company_id.id,
                "partner_id": self.partner_id.id if self.partner_id else False,
                "line_ids": [
                    (0, 0, line_liquidity),
                    (0, 0, line_counterpart),
                ],
            }
        )
        move.action_post()

        Run.create(
            {
                "recurring_id": self.id,
                "run_date": run_date,
                "move_id": move.id,
            }
        )
        self.write(
            {
                "last_run_date": run_date,
                "next_date": self._advance_next_date(run_date),
            }
        )
        return move

    def action_run_now(self):
        for rec in self:
            rec._generate_move(run_date=fields.Date.context_today(rec))
        return True

    @api.model
    def _cron_generate(self):
        """Daily cron: generate moves for due recurring items."""
        today = fields.Date.context_today(self)
        due = self.search(
            [
                ("active", "=", True),
                ("next_date", "<=", today),
            ]
        )
        for rec in due:
            # Catch up: keep generating while next_date <= today (cap iterations)
            safety = 0
            while rec.next_date and rec.next_date <= today and safety < 36:
                try:
                    rec._generate_move(run_date=rec.next_date)
                except Exception:
                    # Don't abort the whole cron; log and skip this record
                    _logger.exception(
                        "Failed to generate recurring %s (id=%s)",
                        rec.name,
                        rec.id,
                    )
                    break
                safety += 1
                # reload next_date
                rec.invalidate_recordset(["next_date"])
        return True


class NeracaRecurringRun(models.Model):
    _name = "neraca.recurring.run"
    _description = "Log Eksekusi Transaksi Berulang"
    _order = "run_date desc, id desc"

    recurring_id = fields.Many2one(
        "neraca.recurring",
        string="Berulang",
        required=True,
        ondelete="cascade",
        index=True,
    )
    run_date = fields.Date(string="Tanggal", required=True, index=True)
    move_id = fields.Many2one(
        "account.move",
        string="Jurnal Entri",
        ondelete="set null",
    )
    company_id = fields.Many2one(
        related="recurring_id.company_id",
        store=True,
    )

    _sql_constraints = [
        (
            "recurring_run_date_uniq",
            "unique(recurring_id, run_date)",
            "Transaksi berulang sudah dijalankan untuk tanggal ini.",
        ),
    ]
