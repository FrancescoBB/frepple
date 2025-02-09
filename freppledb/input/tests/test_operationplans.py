#
# Copyright (C) 2022 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.test import TestCase

from freppledb.common.models import Parameter, Notification
from freppledb.input.models import (
    Calendar,
    CalendarBucket,
    DistributionOrder,
    Item,
    ItemDistribution,
    ItemSupplier,
    Location,
    ManufacturingOrder,
    Operation,
    OperationMaterial,
    OperationPlan,
    OperationPlanMaterial,
    OperationPlanResource,
    OperationResource,
    PurchaseOrder,
    Resource,
    Supplier,
)
from freppledb.output.models import ResourceSummary


class OperationplanTest(TestCase):

    maxDiff = None

    if "scenario1" in settings.DATABASES:
        databases = [DEFAULT_DB_ALIAS, "scenario1"]
        database = "scenario1"
    else:
        database = DEFAULT_DB_ALIAS

    def setUp(self):
        os.environ["FREPPLE_TEST"] = "YES"
        super().setUp()

    def tearDown(self):
        Notification.wait()
        del os.environ["FREPPLE_TEST"]
        super().tearDown()

    def assertOperationplan(self, reference, expected):
        # Compare the operationplan as stored in the database
        obj = OperationPlan.objects.using(self.database).get(pk=reference)
        self.assertDictEqual(
            {
                "quantity": float(obj.quantity),
                "startdate": obj.startdate,
                "enddate": obj.enddate,
                "status": obj.status,
                "materials": [
                    (float(i.quantity), i.flowdate, i.item.name)
                    for i in obj.materials.using(self.database).all()
                ],
                "resources": [
                    (float(i.quantity), i.resource.name)
                    for i in obj.resources.using(self.database).all()
                ],
                "interruptions": obj.plan.get("interruptions", []),
            },
            expected,
        )

    def assertOperationPlans(self, expected):
        self.assertListEqual(
            [
                [
                    o.name,
                    o.startdate.strftime("%Y-%m-%d %H:%M:%S"),
                    o.enddate.strftime("%Y-%m-%d %H:%M:%S"),
                    float(o.quantity),
                ]
                for o in OperationPlan.objects.using(self.database).order_by(
                    "name", "item_id", "startdate", "reference"
                )
            ],
            expected,
        )

    def assertResourcePlan(self, resource, expected):
        d = {}
        for i in (
            ResourceSummary.objects.using(self.database)
            .filter(resource=resource)
            .filter(load__gt=0)
        ):
            d[i.startdate.strftime("%Y-%m-%d %H:%M:%S")] = float(i.load)
        self.assertDictEqual(
            d,
            expected,
        )

    def test_manufacturing_orders(self):

        cal = Calendar(name="working hours", defaultvalue=0)
        cal.save(using=self.database)
        CalendarBucket(
            calendar=cal,
            value=1,
            monday=True,
            tuesday=True,
            wednesday=True,
            friday=True,
            saturday=True,
            sunday=True,
            starttime=time(9, 0, 0),
            endtime=time(16, 59, 59),
        ).save(using=self.database)

        loc = Location(name="factory", available=cal)
        loc.save(using=self.database)
        oper = Operation(
            name="test1",
            type="time_per",
            location=loc,
            duration=timedelta(hours=1),
            duration_per=timedelta(hours=1),
            # sizeminimum=10,
            sizemultiple=20,
            # sizemaximum=14,
        )
        oper.save(using=self.database)

        item1 = Item(name="item1")
        item1.save(using=self.database)
        OperationMaterial(operation=oper, type="end", item=item1, quantity=2).save(
            using=self.database
        )

        item2 = Item(name="item2")
        item2.save(using=self.database)
        OperationMaterial(operation=oper, type="start", item=item2, quantity=-1).save(
            using=self.database
        )

        # effcal = Calendar(name="varying efficiency", defaultvalue=90)
        # effcal.save(using=self.database)
        # CalendarBucket(
        #     calendar=effcal,
        #     value=80,
        #     monday=True,
        #     tuesday=True,
        #     wednesday=True,
        #     friday=True,
        #     saturday=True,
        #     sunday=True,
        #     startdate=datetime(2020, 1, 1),
        # ).save(using=self.database)
        res = Resource(
            name="machine",
            location=loc,
            type="default",
            maximum=1,
            # efficiency_calendar=effcal,
        )
        res.save(using=self.database)
        OperationResource(operation=oper, resource=res, quantity=1).save(
            using=self.database
        )

        # Simulate output of a planning run
        ResourceSummary.objects.using(self.database).bulk_create(
            [
                ResourceSummary(
                    resource=res, startdate=datetime(2022, 12, 1) + timedelta(n), load=0
                )
                for n in range(300)
            ]
        )

        # Test creation of an operationplan
        opplan = ManufacturingOrder(
            reference="MO #1",
            operation=oper,
            startdate=datetime(2023, 1, 1),
            quantity=4,
            status="approved",
        )
        opplan.update(
            self.database,
            create=True,
            reference=opplan.reference,
            operation=opplan.operation,
            startdate=opplan.startdate,
            quantity=opplan.quantity,
            status=opplan.status,
        )
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan.reference,
            {
                "quantity": 20,
                "startdate": datetime(2023, 1, 1),
                "enddate": datetime(2023, 1, 3, 14),
                "status": "approved",
                "materials": [
                    (40, datetime(2023, 1, 3, 14), "item1"),
                    (-20, datetime(2023, 1, 1), "item2"),
                ],
                "resources": [(1, "machine")],
                "interruptions": [
                    ["2023-01-01 00:00:00", "2023-01-01 09:00:00"],
                    ["2023-01-01 17:00:00", "2023-01-02 09:00:00"],
                    ["2023-01-02 17:00:00", "2023-01-03 09:00:00"],
                ],
            },
        )

        self.assertResourcePlan(
            "machine",
            {
                "2023-01-01 00:00:00": 8,
                "2023-01-02 00:00:00": 8,
                "2023-01-03 00:00:00": 5,
            },
        )

        # Test changing the start date
        opplan.startdate = datetime(2023, 2, 1)
        opplan.update(self.database, startdate=datetime(2023, 2, 1))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 20,
                "startdate": datetime(2023, 2, 1),
                "enddate": datetime(2023, 2, 3, 14),
                "status": "approved",
                "materials": [
                    (40, datetime(2023, 2, 3, 14), "item1"),
                    (-20, datetime(2023, 2, 1), "item2"),
                ],
                "resources": [(1, "machine")],
                "interruptions": [
                    ["2023-02-01 00:00:00", "2023-02-01 09:00:00"],
                    ["2023-02-01 17:00:00", "2023-02-02 09:00:00"],
                    ["2023-02-02 17:00:00", "2023-02-03 09:00:00"],
                ],
            },
        )

        self.assertResourcePlan(
            "machine",
            {
                "2023-02-01 00:00:00": 8,
                "2023-02-02 00:00:00": 8,
                "2023-02-03 00:00:00": 5,
            },
        )

        # Test changing the end date
        opplan.enddate = datetime(2023, 2, 5)
        opplan.update(self.database, enddate=datetime(2023, 2, 5))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 20,
                "startdate": datetime(2023, 2, 2, 12),
                "enddate": datetime(2023, 2, 5),
                "status": "approved",
                "materials": [
                    (40, datetime(2023, 2, 5), "item1"),
                    (-20, datetime(2023, 2, 2, 12), "item2"),
                ],
                "resources": [(1, "machine")],
                "interruptions": [
                    ["2023-02-04 17:00:00", "2023-02-05 00:00:00"],
                    ["2023-02-03 17:00:00", "2023-02-04 09:00:00"],
                    ["2023-02-03 06:00:00", "2023-02-03 09:00:00"],
                    ["2023-02-02 17:00:00", "2023-02-03 06:00:00"],
                ],
            },
        )

        self.assertResourcePlan(
            "machine",
            {
                "2023-02-02 00:00:00": 5,
                "2023-02-03 00:00:00": 8,
                "2023-02-04 00:00:00": 8,
            },
        )

        # Test changing quantity
        opplan.quantity = 30
        opplan.update(self.database, quantity=30)
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 40,
                "startdate": datetime(2023, 2, 2, 12),
                "enddate": datetime(2023, 2, 7, 13),
                "status": "approved",
                "materials": [
                    (80, datetime(2023, 2, 7, 13), "item1"),
                    (-40, datetime(2023, 2, 2, 12), "item2"),
                ],
                "resources": [(1, "machine")],
                "interruptions": [
                    ["2023-02-02 17:00:00", "2023-02-03 09:00:00"],
                    ["2023-02-03 17:00:00", "2023-02-04 09:00:00"],
                    ["2023-02-04 17:00:00", "2023-02-05 09:00:00"],
                    ["2023-02-05 17:00:00", "2023-02-06 09:00:00"],
                    ["2023-02-06 17:00:00", "2023-02-07 09:00:00"],
                ],
            },
        )

        self.assertResourcePlan(
            "machine",
            {
                "2023-02-02 00:00:00": 5,
                "2023-02-03 00:00:00": 8,
                "2023-02-04 00:00:00": 8,
                "2023-02-05 00:00:00": 8,
                "2023-02-06 00:00:00": 8,
                "2023-02-07 00:00:00": 4,
            },
        )

        # Test deletion of the operationplan
        opplan.update(self.database, delete=True)
        opplan.delete(using=self.database)
        self.assertEqual(
            OperationPlan.objects.using(self.database)
            .filter(reference="MO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanMaterial.objects.using(self.database)
            .filter(operationplan__reference="MO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanResource.objects.using(self.database)
            .filter(operationplan__reference="MO #1")
            .count(),
            0,
        )
        self.assertResourcePlan(
            "machine",
            {},
        )

    def test_purchase_orders(self):

        cal = Calendar(name="working hours", defaultvalue=0)
        cal.save(using=self.database)
        CalendarBucket(
            calendar=cal,
            value=1,
            monday=True,
            tuesday=True,
            wednesday=True,
            friday=True,
            saturday=True,
            sunday=True,
            starttime=time(9, 0, 0),
            endtime=time(16, 59, 59),
        ).save(using=self.database)

        loc = Location(name="factory", available=cal)
        loc.save(using=self.database)
        supplier = Supplier(name="My supplier")
        supplier.save(using=self.database)

        item = Item(name="item1")
        item.save(using=self.database)
        ItemSupplier(
            item=item,
            supplier=supplier,
            location=loc,
            sizemultiple=10,
            leadtime=timedelta(days=7),
        ).save(using=self.database)

        # Test creation of an operationplan
        opplan = PurchaseOrder(
            reference="PO #1",
            item=item,
            location=loc,
            supplier=supplier,
            startdate=datetime(2023, 1, 1),
            quantity=4,
            status="approved",
        )
        opplan.update(
            self.database,
            create=True,
            reference=opplan.reference,
            item=opplan.item,
            location=opplan.location,
            supplier=opplan.supplier,
            startdate=opplan.startdate,
            quantity=opplan.quantity,
            status=opplan.status,
        )
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan.reference,
            {
                "quantity": 10,
                "startdate": datetime(2023, 1, 1),
                "enddate": datetime(2023, 1, 8),
                "status": "approved",
                "materials": [
                    (10, datetime(2023, 1, 8), "item1"),
                ],
                "resources": [],
                "interruptions": [],
            },
        )

        # Test changing the start date
        opplan.startdate = datetime(2023, 2, 1)
        opplan.update(self.database, startdate=datetime(2023, 2, 1))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 10,
                "startdate": datetime(2023, 2, 1),
                "enddate": datetime(2023, 2, 8),
                "status": "approved",
                "materials": [
                    (10, datetime(2023, 2, 8), "item1"),
                ],
                "resources": [],
                "interruptions": [],
            },
        )

        # Test changing the end date
        opplan.enddate = datetime(2023, 2, 5)
        opplan.update(self.database, enddate=datetime(2023, 2, 5))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 10,
                "startdate": datetime(2023, 1, 29),
                "enddate": datetime(2023, 2, 5),
                "status": "approved",
                "materials": [
                    (10, datetime(2023, 2, 5), "item1"),
                ],
                "resources": [],
                "interruptions": [],
            },
        )

        # Test changing quantity
        opplan.quantity = 20
        opplan.update(self.database, quantity=20)
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 20,
                "startdate": datetime(2023, 1, 29),
                "enddate": datetime(2023, 2, 5),
                "status": "approved",
                "materials": [
                    (20, datetime(2023, 2, 5), "item1"),
                ],
                "resources": [],
                "interruptions": [],
            },
        )

        # Test deletion of the operationplan
        opplan.update(self.database, delete=True)
        opplan.delete(using=self.database)
        self.assertEqual(
            OperationPlan.objects.using(self.database)
            .filter(reference="PO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanMaterial.objects.using(self.database)
            .filter(operationplan__reference="PO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanResource.objects.using(self.database)
            .filter(operationplan__reference="PO #1")
            .count(),
            0,
        )

    def test_distribution_orders(self):

        cal = Calendar(name="working hours", defaultvalue=0)
        cal.save(using=self.database)
        CalendarBucket(
            calendar=cal,
            value=1,
            monday=True,
            tuesday=True,
            wednesday=True,
            friday=True,
            saturday=True,
            sunday=True,
            starttime=time(9, 0, 0),
            endtime=time(16, 59, 59),
        ).save(using=self.database)

        loc1 = Location(name="factory", available=cal)
        loc1.save(using=self.database)
        loc2 = Location(name="warehouse", available=cal)
        loc2.save(using=self.database)

        item = Item(name="item1")
        item.save(using=self.database)
        ItemDistribution(
            location=loc2, origin=loc1, item=item, leadtime=timedelta(days=1)
        ).save(using=self.database)

        # Test creation of an operationplan
        opplan = DistributionOrder(
            reference="DO #1",
            destination=loc2,
            origin=loc1,
            item=item,
            startdate=datetime(2023, 1, 1),
            quantity=4,
            status="approved",
        )
        opplan.update(
            self.database,
            create=True,
            reference=opplan.reference,
            destination=opplan.destination,
            origin=opplan.origin,
            item=opplan.item,
            startdate=opplan.startdate,
            quantity=opplan.quantity,
            status=opplan.status,
        )
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan.reference,
            {
                "quantity": 4,
                "startdate": datetime(2023, 1, 1),
                "enddate": datetime(2023, 1, 3, 17),
                "status": "approved",
                "materials": [
                    (-4, datetime(2023, 1, 1), "item1"),
                    (4, datetime(2023, 1, 3, 17), "item1"),
                ],
                "resources": [],
                "interruptions": [
                    ["2023-01-01 00:00:00", "2023-01-01 09:00:00"],
                    ["2023-01-01 17:00:00", "2023-01-02 09:00:00"],
                    ["2023-01-02 17:00:00", "2023-01-03 09:00:00"],
                ],
            },
        )

        # Test changing the start date
        opplan.startdate = datetime(2023, 2, 1)
        opplan.update(self.database, startdate=datetime(2023, 2, 1))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 4,
                "startdate": datetime(2023, 2, 1),
                "enddate": datetime(2023, 2, 3, 17),
                "status": "approved",
                "materials": [
                    (-4, datetime(2023, 2, 1), "item1"),
                    (4, datetime(2023, 2, 3, 17), "item1"),
                ],
                "resources": [],
                "interruptions": [
                    ["2023-02-01 00:00:00", "2023-02-01 09:00:00"],
                    ["2023-02-01 17:00:00", "2023-02-02 09:00:00"],
                    ["2023-02-02 17:00:00", "2023-02-03 09:00:00"],
                ],
            },
        )

        # Test changing the end date
        opplan.enddate = datetime(2023, 2, 5)
        opplan.update(self.database, enddate=datetime(2023, 2, 5))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 4,
                "startdate": datetime(2023, 2, 2, 9),
                "enddate": datetime(2023, 2, 5),
                "status": "approved",
                "materials": [
                    (-4, datetime(2023, 2, 2, 9), "item1"),
                    (4, datetime(2023, 2, 5), "item1"),
                ],
                "resources": [],
                "interruptions": [
                    ["2023-02-04 17:00:00", "2023-02-05 00:00:00"],
                    ["2023-02-03 17:00:00", "2023-02-04 09:00:00"],
                    ["2023-02-03 00:00:00", "2023-02-03 09:00:00"],
                    ["2023-02-02 17:00:00", "2023-02-03 00:00:00"],
                ],
            },
        )

        # Test changing quantity
        opplan.quantity = 6
        opplan.update(self.database, quantity=6)
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 6,
                "startdate": datetime(2023, 2, 2, 9),
                "enddate": datetime(2023, 2, 4, 17),
                "status": "approved",
                "materials": [
                    (-6, datetime(2023, 2, 2, 9), "item1"),
                    (6, datetime(2023, 2, 4, 17), "item1"),
                ],
                "resources": [],
                "interruptions": [
                    ["2023-02-02 17:00:00", "2023-02-03 09:00:00"],
                    ["2023-02-03 17:00:00", "2023-02-04 09:00:00"],
                ],
            },
        )

        # Test deletion of the operationplan
        opplan.update(self.database, delete=True)
        opplan.delete(using=self.database)
        self.assertEqual(
            OperationPlan.objects.using(self.database)
            .filter(reference="DO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanMaterial.objects.using(self.database)
            .filter(operationplan__reference="DO #1")
            .count(),
            0,
        )
        self.assertEqual(
            OperationPlanResource.objects.using(self.database)
            .filter(operationplan__reference="DO #1")
            .count(),
            0,
        )

    def test_routing_manufacturing_orders(self):

        cal = Calendar(name="working hours", defaultvalue=0)
        cal.save(using=self.database)
        CalendarBucket(
            calendar=cal,
            value=1,
            monday=True,
            tuesday=True,
            wednesday=True,
            friday=True,
            saturday=True,
            sunday=True,
            starttime=time(9, 0, 0),
            endtime=time(16, 59, 59),
        ).save()

        loc = Location(name="factory", available=cal)
        loc.save(using=self.database)
        oper = Operation(
            name="routing",
            type="routing",
            location=loc,
        )
        oper.save(using=self.database)
        oper1 = Operation(
            name="routing step 1",
            type="time_per",
            location=loc,
            duration=timedelta(hours=1),
            duration_per=timedelta(hours=1),
            owner=oper,
            priority=1,
        )
        oper1.save(using=self.database)
        oper2 = Operation(
            name="routing step 2",
            type="time_per",
            location=loc,
            duration=timedelta(hours=1),
            duration_per=timedelta(hours=1),
            owner=oper,
            priority=2,
        )
        oper2.save(using=self.database)
        oper3 = Operation(
            name="routing step 3",
            type="time_per",
            location=loc,
            duration=timedelta(hours=1),
            duration_per=timedelta(hours=1),
            owner=oper,
            priority=3,
        )
        oper3.save(using=self.database)

        item1 = Item(name="item1")
        item1.save(using=self.database)
        OperationMaterial(operation=oper3, type="end", item=item1, quantity=2).save(
            using=self.database
        )

        item2 = Item(name="item2")
        item2.save(using=self.database)
        OperationMaterial(operation=oper1, type="start", item=item2, quantity=-1).save(
            using=self.database
        )

        res = Resource(name="machine", location=loc, type="default", maximum=1)
        res.save(using=self.database)
        OperationResource(operation=oper1, resource=res, quantity=1).save(
            using=self.database
        )
        OperationResource(operation=oper2, resource=res, quantity=1).save(
            using=self.database
        )
        OperationResource(operation=oper3, resource=res, quantity=1).save(
            using=self.database
        )

        # Simulate output of a planning run
        ResourceSummary.objects.using(self.database).bulk_create(
            [
                ResourceSummary(
                    resource=res, startdate=datetime(2022, 12, 1) + timedelta(n), load=0
                )
                for n in range(300)
            ]
        )

        # Test creation of an operationplan
        opplan = ManufacturingOrder(
            reference="MO1",
            operation=oper,
            startdate=datetime(2023, 1, 1),
            quantity=4,
            status="approved",
        )
        opplan.update(
            self.database,
            create=True,
            reference=opplan.reference,
            operation=opplan.operation,
            startdate=opplan.startdate,
            quantity=opplan.quantity,
            status=opplan.status,
        )
        opplan.save(using=self.database)
        opplan1 = ManufacturingOrder(
            reference="MO1 #1",
            operation=oper1,
            startdate=opplan.startdate,
            quantity=4,
            status="approved",
            owner=opplan,
        )
        opplan1.update(
            self.database,
            create=True,
            reference=opplan1.reference,
            operation=opplan1.operation,
            startdate=opplan1.startdate,
            quantity=opplan1.quantity,
            status=opplan1.status,
        )
        opplan1.save(using=self.database)
        opplan2 = ManufacturingOrder(
            reference="MO1 #2",
            operation=oper2,
            startdate=opplan1.enddate,
            quantity=4,
            status="approved",
            owner=opplan,
        )
        opplan2.update(
            self.database,
            create=True,
            reference=opplan2.reference,
            operation=opplan2.operation,
            startdate=opplan2.startdate,
            quantity=opplan2.quantity,
            status=opplan2.status,
        )
        opplan2.save(using=self.database)
        opplan3 = ManufacturingOrder(
            reference="MO1 #3",
            operation=oper3,
            startdate=opplan2.enddate,
            quantity=4,
            status="approved",
            owner=opplan,
        )
        opplan3.update(
            self.database,
            create=True,
            reference=opplan3.reference,
            operation=opplan3.operation,
            startdate=opplan3.startdate,
            quantity=opplan3.quantity,
            status=opplan3.status,
        )
        opplan3.save(using=self.database)

        self.assertOperationplan(
            opplan3.reference,
            {
                "quantity": 4.0,
                "startdate": datetime(2023, 1, 2, 11),
                "enddate": datetime(2023, 1, 2, 16),
                "status": "approved",
                "materials": [(8.0, datetime(2023, 1, 2, 16, 0), "item1")],
                "resources": [(1.0, "machine")],
                "interruptions": [],
            },
        )
        self.assertResourcePlan(
            "machine",
            {"2023-01-01 00:00:00": 8, "2023-01-02 00:00:00": 7},
        )

        # Test changing the start date of the parent
        opplan.startdate = datetime(2023, 2, 1)
        opplan.update(self.database, startdate=datetime(2023, 2, 1))
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 4,
                "startdate": datetime(2023, 2, 1),
                "enddate": datetime(2023, 2, 2, 16),
                "status": "approved",
                "materials": [],
                "resources": [],
                "interruptions": [],
            },
        )
        self.assertResourcePlan(
            "machine",
            {"2023-02-01 00:00:00": 8, "2023-02-02 00:00:00": 7},
        )

        # Test changing the end date of the parent
        opplan.enddate = datetime(2023, 2, 5)
        opplan.update(self.database, enddate=datetime(2023, 2, 5))
        opplan.save(using=self.database)
        self.assertOperationPlans(
            [
                ["routing", "2023-02-03 10:00:00", "2023-02-05 00:00:00", 4.0],
                ["routing step 1", "2023-02-03 10:00:00", "2023-02-03 15:00:00", 4.0],
                ["routing step 2", "2023-02-03 15:00:00", "2023-02-04 12:00:00", 4.0],
                ["routing step 3", "2023-02-04 12:00:00", "2023-02-05 00:00:00", 4.0],
            ]
        )
        self.assertOperationplan(
            opplan,
            {
                "quantity": 4,
                "startdate": datetime(2023, 2, 3, 10),
                "enddate": datetime(2023, 2, 5),
                "status": "approved",
                "materials": [],
                "resources": [],
                "interruptions": [],
            },
        )
        self.assertResourcePlan(
            "machine",
            {"2023-02-03 00:00:00": 7, "2023-02-04 00:00:00": 8},
        )

        # Test changing quantity of the parent
        opplan.quantity = 3
        opplan.update(self.database, quantity=10)
        opplan.save(using=self.database)
        self.assertOperationplan(
            opplan,
            {
                "quantity": 3,
                "startdate": datetime(2023, 2, 3, 10),
                "enddate": datetime(2023, 2, 4, 14),
                "status": "approved",
                "materials": [],
                "resources": [],
                "interruptions": [],
            },
        )
        self.assertResourcePlan(
            "machine",
            {
                "2023-02-03 00:00:00": 7,
                "2023-02-04 00:00:00": 5,
            },
        )

        # Test deletion of the operationplan
        opplan.update(self.database, delete=True)
        opplan.delete(using=self.database)
        self.assertEqual(
            OperationPlan.objects.using(self.database).count(),
            0,
        )
        self.assertEqual(
            OperationPlanMaterial.objects.using(self.database).count(),
            0,
        )
        self.assertEqual(
            OperationPlanResource.objects.using(self.database).count(),
            0,
        )
        self.assertEqual(
            OperationPlanMaterial.objects.using(self.database).count(),
            0,
        )
        self.assertResourcePlan(
            "machine",
            {},
        )
