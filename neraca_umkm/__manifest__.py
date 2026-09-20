# -*- coding: utf-8 -*-
{
    "name": "Neraca for UMKM",
    "version": "18.0.2.0",
    "category": "Accounting/Accounting",
    "summary": "Personal-finance clarity for Indonesian UMKM: wallets, cashflow, budgets, categories, recurring, piutang/utang, P&L",
    "description": """
Neraca for UMKM
===============
Odoo 18 Community addon that brings personal-finance clarity to Indonesian
micro, small, and medium businesses (UMKM).

Features
--------
* **Dompet (Wallets)** — map cash/bank/e-wallet to accounting journals
* **Papan Cashflow** — OWL 2 dashboard with inflow/outflow, runway, projections
* **Kategori** — income/expense categories on journal items + per-category report
* **Berulang** — recurring in/out transactions with daily cron
* **Anggaran** — monthly budget vs actual with over-budget highlights
* **Piutang / Utang lite** — receivable & payable aging views
* **Laporan Laba Rugi UMKM** — simple income vs expense for month / YTD
    """,
    "author": "Fadhil Hanri",
    "website": "https://github.com/fadhilhaka/neraca_umkm",
    "license": "LGPL-3",
    "depends": ["account", "web"],
    "data": [
        "security/neraca_security.xml",
        "security/ir.model.access.csv",
        "data/neraca_wallet_data.xml",
        "data/neraca_category_data.xml",
        "data/neraca_recurring_cron.xml",
        "views/neraca_wallet_views.xml",
        "views/neraca_budget_views.xml",
        "views/neraca_aging_views.xml",
        "views/neraca_cashflow_views.xml",
        "views/neraca_pl_views.xml",
        "views/neraca_category_views.xml",
        "views/neraca_recurring_views.xml",
        "views/neraca_menus.xml",
    ],
    "demo": [
        "demo/neraca_demo.xml",
        "demo/neraca_recurring_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "neraca_umkm/static/src/cashflow_dashboard/cashflow_dashboard.scss",
            "neraca_umkm/static/src/cashflow_dashboard/cashflow_dashboard.js",
            "neraca_umkm/static/src/cashflow_dashboard/cashflow_dashboard.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
