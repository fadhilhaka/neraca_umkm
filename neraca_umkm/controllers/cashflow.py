# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class NeracaCashflowController(http.Controller):
    @http.route(
        "/neraca_umkm/cashflow/data",
        type="json",
        auth="user",
        methods=["POST"],
    )
    def cashflow_data(self):
        return request.env["neraca.cashflow"].get_dashboard_data()
