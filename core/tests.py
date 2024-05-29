import random

import pendulum
from django.test import TestCase

from core.models import Item, Invoice, Procurement, Vendor


class VendorModelTests(TestCase):
    pass


class InvoiceModelTests(TestCase):
    pass


class ProcurementModelTests(TestCase):
    def make_procurements_for_vendor_inside_billing_period(self):
        vendor = Vendor(name="Test Beef Vendor", cutoff_day=15, due_day=-1)
        item = Item(name="Test Saga Beef")
        dt = pendulum.today()
        billing_period_start = vendor.get_cutoff_date(dt.year, dt.month)
        billing_period_end = billing_period_start.subtract(months=1)
        billing_period = billing_period_start.diff(billing_period_end)
        days = {date.day for date in billing_period.range("days")}
        procurements = []
        for date in billing_period.range("days"):
            procurement = Procurement(vendor=vendor, product=)
