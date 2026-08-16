module = env["ir.module.module"].search([("name", "=", "govp_for_odoo")], limit=1)
if not module or module.state != "installed":
    raise RuntimeError("govp_for_odoo is not installed")
module.button_immediate_uninstall()
env.cr.commit()
