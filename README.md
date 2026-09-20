# Neraca for UMKM

**Personal-finance clarity for Indonesian UMKM — on Odoo 18 Community Edition.**

Inspired by Fadhil Hanri's Neraca personal-finance app, upgraded into familiar Odoo Accounting UX: wallets map to journals, cashflow becomes a live board, budgets compare plan vs actual, and piutang/utang stay lightweight.

| | |
|---|---|
| **Technical name** | `neraca_umkm` |
| **Odoo version** | **18.0 Community Edition** (no Enterprise features) |
| **License** | LGPL-3 |
| **Depends** | `account`, `web` |
| **Author** | Fadhil Hanri |

## Features

### 1. Dompet (Wallets) → Journals
Link cash, bank, and e-wallet balances to `account.journal`.

- Types: Tunai / Bank / E-Wallet
- Provider presets: Kas Tunai, BCA, Mandiri, GoPay, OVO, Dana, Other
- Default currency: IDR
- On create: matching cash/bank journal + liquidity account (reuse when possible)
- Computed balance from journal / move lines
- Menu: **Neraca UMKM → Dompet**

### 2. Papan Cashflow (OWL 2 dashboard)
Backend client action under `web.assets_backend`.

- HomeView-style balance summary + Masuk/Keluar split (Neraca iOS paper-&-ink design system)
- Accent `#3E6772`, income moss `#5C744F`, expense brick `#A24E3C`, aged-paper surfaces
- Shadowless cards, capsule CTA with accent glow, count-up metrics, runway ring
- Soft press-scale motion; respects `prefers-reduced-motion`
- Menu: **Neraca UMKM → Papan Cashflow**

### 3. Anggaran (Budget vs actual)
Monthly budget with lines by expense account.

- Variance vs posted expense moves in the period
- Over-budget highlight (list decoration)
- Menu: **Neraca UMKM → Anggaran**

### 4. Piutang & Utang lite
Transient aging from open receivable / payable move line residuals.

- Partner, residual, due date, days overdue
- Menus: **Piutang** / **Utang**

### 5. Laporan Laba Rugi UMKM
Simple income vs expense for current month or YTD, Indonesian labels.

- Menu: **Laporan Laba Rugi UMKM**

## Screenshots

> Placeholders — capture after installing with demo data.

- `[Screenshot: Papan Cashflow dashboard]`
- `[Screenshot: Dompet list & form]`
- `[Screenshot: Anggaran with over-budget highlight]`
- `[Screenshot: Piutang / Utang aging]`
- `[Screenshot: Laba Rugi UMKM]`

## Installation

1. Copy or clone this repository so that the `neraca_umkm` folder is on your Odoo addons path:

   ```bash
   git clone https://github.com/fadhilhaka/neraca_umkm.git
   # addons path should include .../neraca_umkm-repo  (parent of neraca_umkm/)
   ```

2. Update the apps list and install **Neraca for UMKM**.
3. Optionally install with **demo data** enabled for a sample toko/warung (Kas Toko, BCA, GoPay, sample anggaran & partners).

## Repository layout

```
README.md
LICENSE
CHANGELOG.md
neraca_umkm/
  __init__.py
  __manifest__.py
  models/
  views/
  security/
  data/
  demo/
  controllers/
  static/src/cashflow_dashboard/
```

## Security groups

- **Neraca UMKM / User** — day-to-day access (implies Invoice Billing)
- **Neraca UMKM / Manager** — full CRUD on wallets & budgets

Accounting users (`account.group_account_invoice`) also get access via ACL rows.

## Development notes

- Modern Odoo 18 patterns: `@api.model_create_multi`, OWL 2 components, `list` views (not deprecated `tree` as primary tag where list is preferred).
- Indonesian UI labels where natural; English README and code comments.
- CE-only: no Studio, no Enterprise accounting reports.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

[LGPL-3](LICENSE) — same family as Odoo Community.

## v18.0.2.0 — Kategori & Berulang

### Kategori
1. Buka **Neraca UMKM → Kategori** untuk mengelola kategori pendapatan/beban.
2. Saat membuat jurnal, isi **Kategori Neraca** pada baris jurnal (opsional).
3. Lihat ringkasan di **Laporan Per Kategori** atau `top_expense_categories` di Papan Cashflow.

### Berulang
1. Buka **Neraca UMKM → Berulang**, buat jadwal (sewa, gaji, dll) terhubung ke Dompet.
2. Cron harian `Neraca UMKM: Generate Transaksi Berulang` membuat jurnal otomatis.
3. **Jalankan Sekarang** memaksa generate hari ini (idempotent per tanggal).

### Upgrade
```bash
# Dari addons path yang berisi neraca_umkm/
odoo-bin -d YOUR_DB -u neraca_umkm --stop-after-init
```
Atau Apps → Neraca for UMKM → Upgrade.

