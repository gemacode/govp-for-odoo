{
    "name": "GOVP for Odoo",
    "summary": "Emite y comprueba GOVP desde entregas y recepciones",
    "version": "18.0.0.1.0",
    "category": "Inventory/Inventory",
    "license": "AGPL-3",
    "author": "Gemacode",
    "website": "https://gemacode.org",
    "depends": ["stock"],
    "data": [
        "data/ir_cron.xml",
        "views/res_config_settings_views.xml",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
}
