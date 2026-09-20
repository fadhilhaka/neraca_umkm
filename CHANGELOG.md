# Changelog

All notable changes to **Neraca for UMKM** (`neraca_umkm`) are documented in this file.

## [18.0.1.2.0] — 2026-09-20

### Changed
- **Papan Cashflow** restyled to match the Neraca iOS design system (paper & ink):
  - Surfaces: aged-paper page `#F3EEE3`, card `#FBF7EC`, shadowless elevation
  - Accent `#3E6772`, income moss `#5C744F`, expense brick `#A24E3C`
  - Capsule CTA with accent glow; HomeView-style balance summary + income/expense split
  - Soft press-scale motion; respects `prefers-reduced-motion`

## [18.0.1.1.0] — 2026-09-13

### Changed
- **Papan Cashflow** UI refreshed with Zig.ai–inspired motion: teal/coral accents (`#08906C` / `#CE3C2B`), staggered card reveals, KPI count-up, runway progress ring, soft hover lifts
- Skeleton shimmer while loading; respects `prefers-reduced-motion`
- Refined against live zig.ai screenshots: thin-outline metric rings, coral CTA, accent runway panel, `/ 01` panel indexes, off-white canvas

## [18.0.1.0.0] — 2026-09-13

### Added

- Initial Odoo 18 Community Edition release
- **Dompet (`neraca.wallet`)** — wallets linked to cash/bank journals with Indonesian provider presets
- **Papan Cashflow** — OWL 2 dashboard (inflow/outflow/net, runway, 30/60/90 projections)
- **Anggaran (`neraca.budget` / `neraca.budget.line`)** — monthly budget vs actual with over-budget highlight
- **Piutang / Utang lite (`neraca.partner.aging`)** — residual aging for receivables & payables
- **Laporan Laba Rugi UMKM (`neraca.pl.report`)** — month / YTD income vs expense
- Security groups, ACLs, demo data for sample toko/warung
- JSON helper `neraca.cashflow.get_dashboard_data` + optional HTTP JSON route
