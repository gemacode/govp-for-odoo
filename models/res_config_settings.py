from odoo import _, fields, models
from odoo.exceptions import UserError

from .govp_client import GovpExchangeClient, GovpExchangeError


class ResCompany(models.Model):
    _inherit = "res.company"

    govp_exchange_url = fields.Char(default="https://partners.gemacode.org/api/exchange", groups="base.group_system")
    govp_exchange_token = fields.Char(groups="base.group_system", copy=False)
    govp_auto_issue_delivery = fields.Boolean(default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    govp_exchange_url = fields.Char(related="company_id.govp_exchange_url", readonly=False)
    govp_exchange_token = fields.Char(related="company_id.govp_exchange_token", readonly=False)
    govp_auto_issue_delivery = fields.Boolean(related="company_id.govp_auto_issue_delivery", readonly=False)

    def action_govp_test_connection(self):
        self.ensure_one()
        if not self.govp_exchange_url or not self.govp_exchange_token:
            raise UserError(_("Indica la URL y el token de GOVP Exchange."))
        try:
            connector = GovpExchangeClient(self.govp_exchange_url, self.govp_exchange_token).inspect()["connector"]
        except (GovpExchangeError, KeyError) as error:
            raise UserError(_("No se pudo validar la conexión: %s") % error) from error
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {"title": _("GOVP Exchange conectado"), "message": connector.get("label", connector.get("id")), "type": "success", "sticky": False}}
