#
# Copyright (C) 2022 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import json
import os
from unittest import skipUnless
import xmlrpc.client

from django.conf import settings
from django.core import management
from django.test import TransactionTestCase
from django.contrib.auth.models import Group

from freppledb.common.models import User
from freppledb.input.models import Item, PurchaseOrder, ManufacturingOrder
from .management.commands.odoo_container import Command as odoo_container_command
from .utils import getOdooVersion


@skipUnless("freppledb.odoo" in settings.INSTALLED_APPS, "App not activated")
class OdooTest(TransactionTestCase):
    def setUp(self):
        os.environ["FREPPLE_TEST"] = "YES"
        if not User.objects.filter(username="admin").count():
            User.objects.create_superuser("admin", "your@company.com", "admin")
        management.call_command(
            "odoo_container", "--full", "--nolog", "--verbosity", "0"
        )
        # Use the next line to avoid full rebuild
        # management.call_command("odoo_container",  "--verbosity", "0")
        self.client.login(username="admin", password="admin")
        super().setUp()

    def tearDown(self):
        # Comment out the next line to avoid deleting the container at the end of the test
        # management.call_command("odoo_container", "--destroy", "--verbosity", "0")
        del os.environ["FREPPLE_TEST"]
        super().tearDown()

    def odooRPCinit(self, db=None, username=None, password=None, url=None):
        """
        Initialize an XMLRPC connection to the odoo instance
        """
        self.odooversion = getOdooVersion()
        self.db = db or "odoo_frepple_%s" % self.odooversion
        self.url = url or "http://localhost:8069"
        self.username = username or "admin"
        self.password = password or "admin"
        common = xmlrpc.client.ServerProxy("{}/xmlrpc/2/common".format(self.url))
        self.uid = common.authenticate(self.db, self.username, self.password, {})
        self.models = xmlrpc.client.ServerProxy("{}/xmlrpc/2/object".format(self.url))

    def odooRPC(self, odoo_model, odoo_filter=[], odoo_options={}, odoo_fields=None):
        ids = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            odoo_model,
            "search",
            [odoo_filter],
            odoo_options,
        )
        return self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            odoo_model,
            "read",
            [ids],
            {"fields": odoo_fields} if odoo_fields else {},
        )

    def test_odoo_e2e(self):
        # Import odoo data
        self.assertEqual(Item.objects.all().count(), 0)
        management.call_command("odoo_import")
        self.assertGreater(Item.objects.all().count(), 0)

        # Check user sync
        self.assertEqual(Group.objects.filter(name__icontains="odoo").count(), 1)
        self.assertEqual(User.objects.get(username="admin").groups.all().count(), 1)

        # Check input data
        self.assertEqual(Item.objects.all().exclude(name__contains="[").count(), 7)
        po_list = (
            PurchaseOrder.objects.all()
            .exclude(item__name__contains="[")
            .filter(status="confirmed")
        )
        self.assertEqual(po_list.count(), 1)
        po = po_list[0]
        self.assertEqual(po.quantity, 15)
        # TODO receipt date changes between runs, making it difficult to compare here
        # self.assertEqual(po.receipt_date, datetime.today() + timedelta)
        self.assertEqual(
            ManufacturingOrder.objects.all()
            .exclude(item__name__contains="[")
            .filter(status="confirmed")
            .count(),
            0,  # TODO add draft and confirmed PO in demo dataset
        )
        self.assertEqual(
            ManufacturingOrder.objects.all().filter(status="proposed").count(),
            0,
        )
        self.assertEqual(
            PurchaseOrder.objects.all().filter(status="proposed").count(),
            0,
        )

        # Generate plan
        management.call_command(
            "runplan", plantype=1, constraint=15, env="supply,fcst,invplan"
        )

        # Check plan results
        proposed_mo = (
            ManufacturingOrder.objects.all()
            .exclude(item__name__contains="[")
            .filter(status="proposed", owner__isnull=True)
            .order_by("startdate", "operation")
            .first()
        )
        proposed_po = (
            PurchaseOrder.objects.all()
            .exclude(item__name__contains="[")
            .filter(status="proposed")
            .order_by("startdate", "supplier", "item")
            .first()
        )
        self.assertIsNotNone(proposed_mo)
        self.assertIsNotNone(proposed_po)

        # Approve proposed transactions
        response = self.client.post(
            "/erp/upload/",
            json.dumps(
                [
                    {
                        "reference": proposed_mo.reference,
                        "type": "MO",
                    }
                ]
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            "/erp/upload/",
            json.dumps(
                [
                    {
                        "reference": proposed_po.reference,
                        "type": "PO",
                    }
                ]
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        # Check new status
        approved_mo = ManufacturingOrder.objects.get(pk=proposed_mo.reference)
        self.assertEqual(approved_mo.status, "approved")
        approved_po = PurchaseOrder.objects.get(pk=proposed_po.reference)
        self.assertEqual(approved_po.status, "approved")

        # Check results in odoo
        self.odooRPCinit()
        cnt = 0
        for odoo_mo in self.odooRPC(
            "mrp.production", [("origin", "=", "frePPLe"), ("state", "=", "draft")]
        ):
            self.assertEqual(approved_mo.quantity, odoo_mo["product_qty"])
            self.assertEqual(
                approved_mo.startdate.strftime("%Y-%m-%d %H:%M:%S"),
                odoo_mo["date_planned_start"],
            )
            self.assertTrue(odoo_mo["bom_id"][1] in approved_mo.operation.name)
            cnt += 1
        self.assertEqual(cnt, 1)
        cnt = 0
        for odoo_poline in self.odooRPC(
            "purchase.order.line",
            [("order_id.origin", "=", "frePPLe"), ("order_id.state", "=", "draft")],
        ):
            self.assertEqual(approved_po.quantity, odoo_poline["product_qty"])
            self.assertEqual(approved_po.item.name, odoo_poline["product_id"][1])
            self.assertEqual(
                approved_po.enddate.strftime("%Y-%m-%d %H:%M:%S"),
                odoo_poline["date_planned"],
            )
            cnt += 1
        self.assertEqual(cnt, 1)
