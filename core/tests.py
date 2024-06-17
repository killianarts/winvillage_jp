import random

import pendulum
from django.test import TestCase
from django.utils.timezone import get_default_timezone
from djmoney.money import Money
from freezegun import freeze_time
from hordak import models as hordak_models
from winadmin.tasks import create_invoices_task

from core.models import Invoice, Item, Procurement, Vendor


class VendorModelTests(TestCase):
    pass


class InvoiceModelTests(TestCase):
    pass


def make_procurement(
    vendor,
    item_name,
    procured_on,
    price_per_unit=777,
    quantity=7,
    tz=get_default_timezone(),
):
    if not procured_on:
        procured_on = pendulum.today(tz=tz).start_of("month")
    item, created = Item.objects.get_or_create(name=item_name, price=price_per_unit * 2)
    procurement = Procurement.objects.create(
        vendor=vendor,
        product=item,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(hours=1),
    )


def make_procurements(vendor, item_name, price_per_unit, quantity, procured_on):
    p1 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on,
    )
    p2 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=1),
    )
    p3 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=2),
    )
    p4 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=3),
    )
    p5 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=2, days=4),
    )
    p6 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=1, days=3),
    )
    p7 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=3, days=5),
    )
    p8 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.end_of("month"),
    )
    p9 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(days=5),
    )
    p10 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        procured_on=procured_on.add(weeks=1, days=4),
    )


class ProcurementAndInvoiceModelTests(TestCase):
    def setUp(self):
        dairy_peddler = Vendor.objects.create(
            name="Clyde&Jane Dairy Folks", cutoff_day=-1, due_day=-1
        )
        beef_peddler = Vendor.objects.create(
            name="Tender Cow Parts", cutoff_day=15, due_day=-1
        )
        drink_peddler = Vendor.objects.create(
            name="Hydration Experts Inc.", cutoff_day=5, due_day=12
        )
        tz = get_default_timezone()
        april = pendulum.datetime(2024, 4, 1, tz=tz)
        may = pendulum.datetime(2024, 5, 1, tz=tz)
        june = pendulum.datetime(2024, 6, 1, tz=tz)
        make_procurements(
            vendor=dairy_peddler,
            item_name="Heavy Cream",
            price_per_unit=1900,
            quantity=5,
            procured_on=april,
        )
        make_procurements(
            vendor=dairy_peddler,
            item_name="Blue Cheese",
            price_per_unit=777,
            quantity=7,
            procured_on=may,
        )
        make_procurements(
            vendor=dairy_peddler,
            item_name="Yoghurt",
            price_per_unit=250,
            quantity=10,
            procured_on=june,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Saga Beef Cubes",
            price_per_unit=3000,
            quantity=5,
            procured_on=april,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Big American Steak",
            price_per_unit=4500,
            quantity=7,
            procured_on=may,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Milky Udder Patties",
            price_per_unit=2250,
            quantity=10,
            procured_on=june,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="FlatBeer",
            price_per_unit=3000,
            quantity=5,
            procured_on=april,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="Fizzy Purple Stuff",
            price_per_unit=4500,
            quantity=7,
            procured_on=may,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="Old Man Sweat",
            price_per_unit=2250,
            quantity=10,
            procured_on=june,
        )

    def test_get_dairy_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Clyde&Jane Dairy Folks")
        cutoff_date = vendor.get_cutoff_date(dt.year, dt.month)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = Procurement.objects.filter(
            vendor=vendor,
            procured_on__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("procured_on")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {procurement.vendor.name}")
            print(f"Cutoff Date: {cutoff_date}")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.procured_on}")
            print("--------------------------------------------------")

    def test_get_beef_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Tender Cow Parts")
        cutoff_date = vendor.get_cutoff_date(dt.year, dt.month)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = Procurement.objects.filter(
            vendor=vendor,
            procured_on__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("procured_on")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {procurement.vendor.name}")
            print(f"Cutoff Date: {cutoff_date}")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.procured_on}")
            print("--------------------------------------------------")

    def test_get_drink_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Hydration Experts Inc.")
        cutoff_date = vendor.get_cutoff_date(dt.year, dt.month)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = Procurement.objects.filter(
            vendor=vendor,
            procured_on__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("procured_on")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {procurement.vendor.name}")
            print(f"Invoice Period: {cutoff_date.subtract(months=1)} - { cutoff_date }")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.procured_on}")
            print("--------------------------------------------------")

    @freeze_time("2024-5-15")
    def test_create_tender_cow_parts_invoice_task(self):
        """This should an invoice for tender cow parts."""
        responses = create_invoices_task()
        self.assertTrue(responses)

    @freeze_time("2024-5-16")
    def test_create_no_invoice_task(self):
        """This shouldn't produce any invoices. Tender Cow Parts invoiced yesterday."""
        responses = create_invoices_task()
        self.assertFalse(responses)
