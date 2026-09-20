/** @odoo-module **/

import { Component, onWillStart, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const REDUCED_MOTION =
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

export class CashflowDashboard extends Component {
    static template = "neraca_umkm.CashflowDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.ringRef = useRef("runwayRing");
        this._raf = null;
        this.state = useState({
            loading: true,
            error: null,
            data: null,
            display: {
                inflow: 0,
                outflow: 0,
                net: 0,
                balance: 0,
                d30: 0,
                d60: 0,
                d90: 0,
            },
            ringPct: 0,
        });
        onWillStart(async () => {
            await this.loadData();
        });
        onWillUnmount(() => {
            if (this._raf) {
                cancelAnimationFrame(this._raf);
            }
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const data = await this.orm.call("neraca.cashflow", "get_dashboard_data", []);
            this.state.data = data;
            this._animateNumbers(data);
            this._animateRing(data);
        } catch (e) {
            this.state.error = e.message || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    _animateNumbers(data) {
        if (this._raf) {
            cancelAnimationFrame(this._raf);
        }
        const targets = {
            inflow: Number(data.inflow || 0),
            outflow: Number(data.outflow || 0),
            net: Number(data.net || 0),
            balance: Number(data.balance || 0),
            d30: Number(data.projections?.d30 || 0),
            d60: Number(data.projections?.d60 || 0),
            d90: Number(data.projections?.d90 || 0),
        };
        if (REDUCED_MOTION) {
            Object.assign(this.state.display, targets);
            return;
        }
        const from = { ...this.state.display };
        const duration = 700;
        const start = performance.now();
        const tick = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const e = easeOutCubic(t);
            for (const key of Object.keys(targets)) {
                this.state.display[key] = from[key] + (targets[key] - from[key]) * e;
            }
            if (t < 1) {
                this._raf = requestAnimationFrame(tick);
            } else {
                Object.assign(this.state.display, targets);
                this._raf = null;
            }
        };
        this._raf = requestAnimationFrame(tick);
    }

    _animateRing(data) {
        const days = data.runway_days;
        let pct = 0;
        if (days !== null && days !== undefined && days >= 0) {
            pct = Math.min(100, (days / 90) * 100);
        }
        if (REDUCED_MOTION) {
            this.state.ringPct = pct;
            this._applyRing(pct);
            return;
        }
        const from = this.state.ringPct;
        const start = performance.now();
        const duration = 800;
        const step = (now) => {
            const t = Math.min(1, (now - start) / duration);
            const e = easeOutCubic(t);
            const value = from + (pct - from) * e;
            this.state.ringPct = value;
            this._applyRing(value);
            if (t < 1) {
                requestAnimationFrame(step);
            }
        };
        requestAnimationFrame(step);
    }

    _applyRing(pct) {
        const el = this.ringRef.el;
        if (el) {
            el.style.setProperty("--neraca-ring-p", String(pct));
        }
    }

    formatMoney(amount) {
        const data = this.state.data;
        if (!data) {
            return String(amount ?? 0);
        }
        const { symbol, position, decimal_places } = data.currency;
        const n = Number(amount || 0);
        const formatted = n.toLocaleString("id-ID", {
            minimumFractionDigits: decimal_places,
            maximumFractionDigits: decimal_places,
        });
        return position === "after" ? `${formatted} ${symbol}` : `${symbol} ${formatted}`;
    }

    get runwayLabel() {
        const d = this.state.data?.runway_days;
        if (d === null || d === undefined) {
            return "—";
        }
        if (d < 0) {
            return "Perlu perhatian";
        }
        return `${d} hari`;
    }

    get ringCenterLabel() {
        const d = this.state.data?.runway_days;
        if (d === null || d === undefined) {
            return "—";
        }
        if (d < 0) {
            return "!";
        }
        return `${Math.min(99, d)}d`;
    }
}

registry.category("actions").add("neraca_umkm_cashflow_dashboard", CashflowDashboard);
