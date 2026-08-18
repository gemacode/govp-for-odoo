import hashlib
import json
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .govp_client import GovpExchangeClient, GovpExchangeError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    govp_code = fields.Char(copy=False, readonly=True)
    govp_verify_url = fields.Char(copy=False, readonly=True)
    govp_status = fields.Selection([("none", "Sin GOVP"), ("pending", "Pendiente"), ("valid", "Válido"), ("revoked", "Revocado"), ("error", "Incidencia")], default="none", copy=False, readonly=True)
    govp_error = fields.Text(copy=False, readonly=True)

    def _govp_completed_at(self):
        self.ensure_one()
        completed = self.date_done or self.scheduled_date or self.create_date
        if not completed:
            raise UserError(_("La entrega necesita una fecha estable antes de emitir GOVP."))
        return fields.Datetime.to_datetime(completed)

    def _govp_idempotency_key(self):
        self.ensure_one()
        completed = fields.Datetime.to_string(self._govp_completed_at())
        return "odoo:stock.picking:%s:%s:%s" % (self.company_id.id, self.id, completed.replace(" ", "T"))

    def _govp_evidence_lines(self):
        self.ensure_one()
        lines = []
        for line in self.move_line_ids.filtered(lambda item: item.quantity):
            lines.append({
                "product": line.product_id.default_code or str(line.product_id.id),
                "quantity": line.quantity,
                "uom": line.product_uom_id.name,
                "lot": line.lot_id.name or line.lot_name or None,
            })
        if not lines:
            lines = [{
                "product": move.product_id.default_code or str(move.product_id.id),
                "quantity": move.quantity,
                "uom": move.product_uom.name,
                "lot": None,
            } for move in self.move_ids if move.quantity]
        return sorted(lines, key=lambda item: (
            item["product"], item["lot"] or "", item["uom"], str(item["quantity"]),
        ))

    def _govp_payload(self):
        self.ensure_one()
        lines = self._govp_evidence_lines()
        digest = hashlib.sha256(json.dumps(lines, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return {
            "issuer": {"name": self.company_id.name, "email": self.company_id.email or None},
            "recipient": {"name": self.partner_id.commercial_company_name or self.partner_id.name},
            "subject": {"type": "shipment", "id": self.name, "name": _("Expedición %s") % self.name, "description": self.origin or None},
            "requirement": _("Demostrar la expedición y sus líneas antes de aceptar la recepción."),
            "evidence": [{"label": _("Huella de las líneas de movimiento"), "sha256": digest}],
            "validUntil": fields.Datetime.to_string(self._govp_completed_at() + timedelta(days=365)).replace(" ", "T") + "Z",
            "source": {"platform": "odoo", "externalId": self._govp_idempotency_key()},
        }

    def action_govp_issue(self):
        for picking in self:
            if picking.state != "done" or picking.picking_type_code != "outgoing":
                raise UserError(_("El GOVP se emite desde una entrega de salida validada."))
            company = picking.company_id
            if not company.govp_exchange_url or not company.govp_exchange_token:
                raise UserError(_("Configura GOVP Exchange antes de emitir."))
            picking.govp_status = "pending"
            try:
                result = GovpExchangeClient(company.govp_exchange_url, company.govp_exchange_token).issue(picking._govp_payload(), picking._govp_idempotency_key())
                govp = result["govp"]
                picking.write({"govp_code": govp["code"], "govp_verify_url": govp["verifyUrl"], "govp_status": "valid", "govp_error": False})
            except (GovpExchangeError, KeyError) as error:
                picking.write({"govp_status": "error", "govp_error": str(error)[:1000]})
        return True

    def action_govp_verify(self):
        self.ensure_one()
        if not self.govp_code:
            raise UserError(_("Esta operación no tiene GOVP."))
        try:
            result = GovpExchangeClient(self.company_id.govp_exchange_url, self.company_id.govp_exchange_token).verify(self.govp_code)
            status = result["verification"]["status"]
            self.write({"govp_status": status if status in {"valid", "revoked"} else "error", "govp_error": False if status in {"valid", "revoked"} else result["verification"].get("reasonCode")})
        except (GovpExchangeError, KeyError) as error:
            self.write({"govp_status": "error", "govp_error": str(error)[:1000]})
        return True

    def button_validate(self):
        result = super().button_validate()
        for picking in self.filtered(lambda item: item.state == "done" and item.picking_type_code == "outgoing" and item.company_id.govp_auto_issue_delivery and not item.govp_code):
            picking.action_govp_issue()
        return result

    @api.model
    def _cron_govp_retry(self):
        for picking in self.search([("govp_status", "=", "error"), ("state", "=", "done"), ("picking_type_code", "=", "outgoing")], limit=50):
            picking.action_govp_issue()
