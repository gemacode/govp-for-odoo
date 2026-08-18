import unittest
from datetime import timedelta

try:
    from odoo.tests import tagged
    from odoo.tests.common import TransactionCase
except ModuleNotFoundError as error:
    raise unittest.SkipTest("requiere el runtime nativo de Odoo") from error


@tagged("post_install", "-at_install")
class GovpStockPickingNativeTest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "GOVP Native Company B"})
        cls.partner = cls.env["res.partner"].create({"name": "GOVP Synthetic Recipient"})
        cls.product = cls.env["product.product"].create({
            "name": "GOVP Synthetic Tracked Product",
            "default_code": "GOVP-NATIVE-LOT",
            "is_storable": True,
            "tracking": "lot",
        })

    def _picking(self, company):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", company.id)], limit=1)
        if not warehouse:
            warehouse = self.env["stock.warehouse"].create({"name": "GOVP Native", "code": "G%s" % company.id, "company_id": company.id})
        return self.env["stock.picking"].with_company(company).create({
            "partner_id": self.partner.id,
            "picking_type_id": warehouse.out_type_id.id,
            "location_id": warehouse.lot_stock_id.id,
            "location_dest_id": self.partner.property_stock_customer.id,
            "company_id": company.id,
        })

    def test_partial_lot_lines_are_canonical_and_hashed(self):
        picking = self._picking(self.company_a)
        move = self.env["stock.move"].create({
            "name": self.product.display_name,
            "product_id": self.product.id,
            "product_uom_qty": 10,
            "product_uom": self.product.uom_id.id,
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "company_id": self.company_a.id,
        })
        lot_b = self.env["stock.lot"].create({"name": "LOT-B", "product_id": self.product.id, "company_id": self.company_a.id})
        lot_a = self.env["stock.lot"].create({"name": "LOT-A", "product_id": self.product.id, "company_id": self.company_a.id})
        for lot, quantity in ((lot_b, 3), (lot_a, 1)):
            self.env["stock.move.line"].create({
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": self.product.id,
                "product_uom_id": self.product.uom_id.id,
                "quantity": quantity,
                "lot_id": lot.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_a.id,
            })
        lines = picking._govp_evidence_lines()
        self.assertEqual([line["lot"] for line in lines], ["LOT-A", "LOT-B"])
        self.assertEqual(sum(line["quantity"] for line in lines), 4)
        self.assertEqual(len(picking._govp_payload()["evidence"][0]["sha256"]), 64)

    def test_idempotency_is_separated_by_company(self):
        picking_a = self._picking(self.company_a)
        picking_b = self._picking(self.company_b)
        self.assertNotEqual(picking_a._govp_idempotency_key(), picking_b._govp_idempotency_key())
        self.assertIn(":%s:" % self.company_a.id, picking_a._govp_idempotency_key())
        self.assertIn(":%s:" % self.company_b.id, picking_b._govp_idempotency_key())

    def test_validity_is_anchored_to_the_stable_picking_date(self):
        picking = self._picking(self.company_a)
        expected = picking._govp_completed_at() + timedelta(days=365)
        first = picking._govp_payload()["validUntil"]
        second = picking._govp_payload()["validUntil"]
        self.assertEqual(first, second)
        self.assertEqual(first, expected.strftime("%Y-%m-%dT%H:%M:%SZ"))
