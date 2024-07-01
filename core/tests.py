import random

import pendulum
from django.db.models import Q, F, When, Value, IntegerField, Case, Sum
from django.test import TestCase
from django.utils.timezone import get_default_timezone
from djmoney.money import Money
from freezegun import freeze_time
from hordak import models as hordak_models
from hordak.models import Account, Leg
from hordak.utilities.currency import Balance
from phonenumber_field.phonenumber import PhoneNumber
from winadmin.tasks import create_invoices_task

from core.accounting_utils import (
    create_default_chart_of_accounts,
    get_accounts_payable_account_from_configuration,
    get_inventory_account_from_configuration,
)
from core.models import Invoice, Item, Procurement, TransactionDetail, Vendor


def make_procurement(
    vendor,
    item_name,
    date,
    price_per_unit=Money(777, "JPY"),
    quantity=7,
    tz=get_default_timezone(),
):
    if not date:
        date = pendulum.today(tz=tz).start_of("month")
    if not isinstance(price_per_unit, Money):
        price_per_unit = Money(price_per_unit, "JPY")
    item, created = Item.objects.get_or_create(name=item_name, price=price_per_unit * 2)
    inventory = get_inventory_account_from_configuration()
    accounts_payable = vendor.account
    transaction = accounts_payable.accounting_transfer_to(
        to_account=inventory, amount=quantity * price_per_unit, date=date
    )
    detail = TransactionDetail.objects.create(
        summary=transaction,
        item=item.name,
        quantity=quantity,
        price_per_unit=price_per_unit,
    )
    return detail


def make_procurements(vendor, item_name, price_per_unit, quantity, date):
    p1 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date,
    )
    p9 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(days=4),
    )

    p2 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=1),
    )
    p6 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=1, days=3),
    )
    p10 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=1, days=4),
    )
    p3 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=2),
    )
    p5 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=2, days=4),
    )
    p4 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=3),
    )

    p7 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.add(weeks=3, days=5),
    )
    p8 = make_procurement(
        vendor,
        item_name,
        price_per_unit=price_per_unit,
        quantity=quantity,
        date=date.end_of("month"),
    )


tz = get_default_timezone()
april = pendulum.date(2024, 4, 1)
end_of_april = april.end_of("month").start_of("day")
april_fifth = april.add(days=4)
april_fifteenth = april.add(days=14)
may = pendulum.date(2024, 5, 1)
end_of_may = may.end_of("month").start_of("day")
may_fifth = may.add(days=4)
may_fifteenth = may.add(days=14)
june = pendulum.date(2024, 6, 1)
end_of_june = june.end_of("month").start_of("day")
june_fifth = june.add(days=4)
june_fifteenth = june.add(days=14)


class ProcurementAndInvoiceModelTests(TestCase):
    def setUp(self):
        create_default_chart_of_accounts()
        dairy_peddler = Vendor.objects.create(
            name="Clyde&Jane Dairy Folks",
            cutoff_day=-1,
            due_day=-1,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="2-6-2 Milky Lane",
            city="Sapporo",
            prefecture="Hokkaido",
        )
        beef_peddler = Vendor.objects.create(
            name="Tender Cow Parts",
            cutoff_day=15,
            due_day=-1,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="5-3-8 Beefy Heights",
            city="Kobe",
            prefecture="Hyogo",
        )
        drink_peddler = Vendor.objects.create(
            name="Hydration Experts Inc.",
            cutoff_day=5,
            due_day=12,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="9-9-9 Hydration Park",
            city="Tokyo",
            prefecture="Tokyo",
        )
        make_procurements(
            vendor=dairy_peddler,
            item_name="Heavy Cream",
            price_per_unit=1900,
            quantity=5,
            date=april,
        )
        make_procurements(
            vendor=dairy_peddler,
            item_name="Blue Cheese",
            price_per_unit=777,
            quantity=7,
            date=may,
        )
        make_procurements(
            vendor=dairy_peddler,
            item_name="Yoghurt",
            price_per_unit=250,
            quantity=10,
            date=june,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Saga Beef Cubes",
            price_per_unit=3000,
            quantity=5,
            date=april,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Big American Steak",
            price_per_unit=4500,
            quantity=7,
            date=may,
        )
        make_procurements(
            vendor=beef_peddler,
            item_name="Milky Udder Patties",
            price_per_unit=2250,
            quantity=10,
            date=june,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="FlatBeer",
            price_per_unit=3000,
            quantity=5,
            date=april,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="Fizzy Purple Stuff",
            price_per_unit=4500,
            quantity=7,
            date=may,
        )
        make_procurements(
            vendor=drink_peddler,
            item_name="Old Man Sweat",
            price_per_unit=2250,
            quantity=10,
            date=june,
        )
        vendors = Vendor.objects.all()
        dt1 = pendulum.date(2024, 1, 1)
        dt2 = dt1.add(years=1)
        interval = pendulum.interval(dt1, dt2)
        for v in vendors:
            for dt in interval.range("days"):
                if dt == v.get_cutoff_date(dt):
                    cutoff = v.get_cutoff_date(dt)
                    previous_dt = dt.subtract(months=1)
                    # .add(days=1) is essential for not double-invoicing anything at the end of the month
                    previous_cutoff = v.get_cutoff_date(
                        previous_dt.year, previous_dt.month
                    ).add(days=1)
                    account = v.account
                    legs = Leg.objects.filter(
                        account=account,
                        transaction__date__range=(
                            previous_cutoff,
                            cutoff,
                        ),
                    )
                    details = TransactionDetail.objects.filter(
                        summary__legs__in=legs
                    ).order_by("summary__date")
                    invoice = v.create_invoice(dt, details)

    def ctest_get_dairy_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Clyde&Jane Dairy Folks")
        account = Account.objects.get(name=vendor.name)
        legs = Leg.objects.filter(account=account)
        cutoff_date = vendor.get_cutoff_date(dt)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = TransactionDetail.objects.filter(
            summary__legs__in=legs,
            summary__date__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("summary__date")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {vendor.name}")
            print(f"Invoice Period: {cutoff_date.subtract(months=1)} - { cutoff_date }")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.summary.date}")
            print("--------------------------------------------------")
            print("")
        print("")

    def ctest_get_beef_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Tender Cow Parts")
        account = Account.objects.get(name=vendor.name)
        legs = Leg.objects.filter(account=account)
        cutoff_date = vendor.get_cutoff_date(dt)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = TransactionDetail.objects.filter(
            summary__legs__in=legs,
            summary__date__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("summary__date")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {vendor.name}")
            print(f"Invoice Period: {cutoff_date.subtract(months=1)} - { cutoff_date }")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.summary.date}")
            print("--------------------------------------------------")
            print("")
        print("")

    def ctest_get_drink_peddler_april_procurements(self):
        dt = pendulum.datetime(2024, 5, 1, tz=get_default_timezone())
        vendor = Vendor.objects.get(name="Hydration Experts Inc.")
        account = Account.objects.get(name=vendor.name)
        legs = Leg.objects.filter(account=account)
        cutoff_date = vendor.get_cutoff_date(dt)
        due_date = vendor.get_due_date(cutoff_date)
        procurements = TransactionDetail.objects.filter(
            summary__legs__in=legs,
            summary__date__range=(
                cutoff_date.subtract(months=1),
                cutoff_date,
            ),
        ).order_by("summary__date")
        # Print the details of each procurement
        for procurement in procurements:
            print("--------------------------------------------------")
            print(f"Vendor: {vendor.name}")
            print(f"Invoice Period: {cutoff_date.subtract(months=1)} - { cutoff_date }")
            print(f"Due Date: {due_date}")
            print(f"Procured On: {procurement.summary.date}")
            print("--------------------------------------------------")
            print("")
        print("")

    @freeze_time(str(may_fifteenth))
    def ctest_create_tender_cow_parts_invoice_task(self):
        """This should produce an invoice for tender cow parts."""
        responses = create_invoices_task()
        self.assertTrue(responses)
        print("")

    @freeze_time("2024-5-16")
    def ctest_create_no_invoice_task(self):
        """This shouldn't produce any invoices. Tender Cow Parts invoiced yesterday."""
        responses = create_invoices_task()
        self.assertFalse(responses)
        print("")

    def ctest_cutoff_and_due_dates(self):
        print(f">>>>>>>>>> Test Cutoff and Due Dates <<<<<<<<<<")
        print("")
        vendors = Vendor.objects.all()
        dt1 = pendulum.datetime(2024, 1, 1, tz=tz)
        dt2 = dt1.add(years=1)
        interval = pendulum.interval(dt1, dt2)
        for v in vendors:
            print(f"=========={v.name}==========")
            for dt in interval.range("days"):
                cutoff_date = v.get_cutoff_date(dt)
                due_date = v.get_due_date(cutoff_date)
                if dt.date() == cutoff_date:
                    print(f"{cutoff_date} is {v}'s cutoff date")
                    print("")
        print("")

    def ctest_invoicing_periods(self):
        print(f">>>>>>>>>> Test Invoicing Periods <<<<<<<<<<")
        vendors = Vendor.objects.all()
        dt1 = pendulum.date(2024, 1, 1)
        dt2 = dt1.add(years=1)
        interval = pendulum.interval(dt1, dt2)
        for dt in interval.range("days"):
            with freeze_time(str(dt)):
                for v in vendors:
                    if dt == v.get_cutoff_date(dt):
                        cutoff = v.get_cutoff_date(dt)
                        previous_dt = dt.subtract(months=1)
                        previous_cutoff = v.get_cutoff_date(previous_dt)
                        account = v.account
                        legs = Leg.objects.filter(
                            account=account,
                            transaction__date__range=(previous_cutoff, cutoff),
                        )
                        details = TransactionDetail.objects.filter(
                            summary__legs__in=legs
                        ).order_by("summary__date")
                        invoice = v.create_invoice(dt, details)

                        print(f"=========={v}==========")
                        print(f"{invoice.vendor}")
                        print(f"Invoiced On {invoice.invoiced_on}")
                        print(f"Invoiced for Period {previous_cutoff} - {cutoff}")
                        print(f"Due On {invoice.due_on}")
                        print(f"Amount: {invoice.amount}")
                        print("")
        print("")

    def ctest_multiple_invoices(self):
        print(f">>>>>>>>>> Test Multiple Invoices <<<<<<<<<<")
        vendors = Vendor.objects.all()
        dt1 = pendulum.date(2024, 1, 1)
        dt2 = dt1.add(years=1)
        interval = pendulum.interval(dt1, dt2)
        for v in vendors:
            for dt in interval.range("days"):
                with freeze_time(str(dt)):
                    if dt == v.get_cutoff_date(dt):
                        cutoff = v.get_cutoff_date(dt)
                        previous_dt = dt.subtract(months=1)
                        # .add(days=1) is essential for not double-invoicing anything at the end of the month
                        previous_cutoff = v.get_cutoff_date(previous_dt).add(days=1)
                        account = v.account
                        legs = Leg.objects.filter(
                            account=account,
                            transaction__date__range=(
                                previous_cutoff,
                                cutoff,
                            ),
                        )
                        details = TransactionDetail.objects.filter(
                            summary__legs__in=legs
                        ).order_by("summary__date")
                        invoice = v.create_invoice(dt, details)

                        print(f"=========={v}==========")
                        print(f"{invoice.vendor}")
                        print(f"Invoiced On {invoice.invoiced_on}")
                        print(f"Invoiced for Period {previous_cutoff} - {cutoff}")
                        print(f"Due On {invoice.due_on}")
                        print(f"Amount: {invoice.amount}")
                        for procurement in details:
                            print("")
                            print(
                                f"{procurement.id} | {procurement.summary.date} - {procurement.item}, {procurement.quantity}, {procurement.price_per_unit}, {procurement.quantity * procurement.price_per_unit}"
                            )
                        print("")

        print("")

    def ctest_end_of_month_cutoff_date_invoicing(self):
        """I expect that all purchase made on the last day of the month to be included in the invoice."""
        print(f">>>>>>>>>> Test End of Month Cutoff Date Invoicing <<<<<<<<<<")
        vendors = Vendor.objects.filter(cutoff_day=-1)
        dt1 = pendulum.date(2024, 1, 1)
        dt2 = dt1.add(years=1)
        interval = pendulum.interval(dt1, dt2)
        for dt in interval.range("days"):
            with freeze_time(str(dt)):
                for v in vendors:
                    if dt == v.get_cutoff_date(dt.year, dt.month):
                        cutoff = v.get_cutoff_date(dt.year, dt.month)
                        previous_dt = dt.subtract(months=1)
                        previous_cutoff = v.get_cutoff_date(
                            previous_dt.year, previous_dt.month
                        ).add(days=1)
                        account = v.account
                        legs = Leg.objects.filter(
                            account=account,
                            transaction__date__range=(
                                previous_cutoff,
                                cutoff,
                            ),
                        )
                        details = TransactionDetail.objects.filter(
                            summary__legs__in=legs
                        ).order_by("summary__date")
                        invoice = v.create_invoice(dt, details)

                        print(f"=========={v}==========")
                        print(f"{invoice.vendor}")
                        print(f"Invoiced On {invoice.invoiced_on}")
                        print(f"Invoiced for Period {previous_cutoff} - {cutoff}")
                        print(f"Due On {invoice.due_on}")
                        print(f"Amount: {invoice.amount}")
                        for procurement in details:
                            print("")
                            print(
                                f"ID: {procurement.id} | {procurement.summary.date} - {procurement.item}, {procurement.quantity}, {procurement.price_per_unit}, {procurement.quantity * procurement.price_per_unit}"
                            )
                        print("")
        print("")

    def ctest_accounts_payable_aging_report(self):
        dt1 = pendulum.date(2024, 4, 15)
        dt2 = pendulum.date(2024, 7, 15)
        interval = pendulum.interval(dt1, dt2)
        for vendor in Vendor.objects.all():
            for dt in interval.range("months"):
                invoices = Invoice.objects.filter(
                    vendor=vendor,
                    invoiced_on__range=(dt.subtract(months=1).add(days=1), dt),
                )
                for invoice in invoices:
                    if invoice.amount > Money(0, "JPY"):
                        print(f"{invoice.vendor}")
                        print(f"Invoiced: {invoice.invoiced_on}")
                        print(f"Due: {invoice.due_on}")
                        print(f"Amount: {invoice.amount}")
                        for procurement in invoice.procurements.all().order_by(
                            "summary__date"
                        ):
                            print(
                                f"ID: {procurement.id} | {procurement.summary.date} - {procurement.item}, {procurement.quantity}, {procurement.price_per_unit}, {procurement.quantity * procurement.price_per_unit}"
                            )

                        cash = Account.objects.get(code=100)
                        transaction = cash.accounting_transfer_to(
                            vendor.account, invoice.amount, date=dt
                        )
                        leg = transaction.legs.get(account=vendor.account)
                        print(f"Balance: {vendor.account.balance()}")
                        print(f"Payment: {leg.amount}")
                        print(f"Before: {leg.id, leg.account_balance_before()}")
                        print(f"After: {leg.account_balance_after()}")
            print("")


class AccountsPayableAgingReportTest(TestCase):
    def setUp(self):
        create_default_chart_of_accounts()

        dairy_peddler = Vendor.objects.create(
            name="Clyde&Jane Dairy Folks",
            cutoff_day=-1,
            due_day=-1,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="2-6-2 Milky Lane",
            city="Sapporo",
            prefecture="Hokkaido",
        )
        beef_peddler = Vendor.objects.create(
            name="Tender Cow Parts",
            cutoff_day=15,
            due_day=-1,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="5-3-8 Beefy Heights",
            city="Kobe",
            prefecture="Hyogo",
        )
        drink_peddler = Vendor.objects.create(
            name="Hydration Experts Inc.",
            cutoff_day=5,
            due_day=12,
            phone=PhoneNumber.from_string("+8107043327278", region="JA"),
            postal_code="064-0941",
            address="9-9-9 Hydration Park",
            city="Tokyo",
            prefecture="Tokyo",
        )

    def test_no_balances(self):
        print("")
        print("<test no balances>")
        print("")
        vendors = Vendor.objects.all()
        balances = []
        for vendor in vendors:
            balances.append(vendor.account.balance())
        print(balances)
        self.assertEqual(balances, [0, 0, 0])
        print("")
        print("</test no balances>")
        print("")

    def xtest_one_month_procurements_and_payment(self):
        print("")
        print("<Dairy Peddler Balance>")
        print("")
        print("(make-procurements dairy-peddler)")
        vendor = Vendor.objects.get(name="Clyde&Jane Dairy Folks")
        make_procurements(vendor, "Milk", Money(500, "JPY"), 1, april)
        legs = Leg.objects.filter(account=vendor.account)
        for leg in legs:
            print(leg.id, leg.account_balance_before(), leg.account_balance_after())
        print(f"Balance: {vendor.balance()}")

        print("(make-invoice)")
        procurements = TransactionDetail.objects.filter(
            summary__legs__account=vendor.account,
            summary__date__range=(april, end_of_april),
        )
        invoice = vendor.create_invoice(may, procurements)
        print(f"Amount: {invoice.amount}")
        print("(make-payment)")
        cash = Account.objects.get(code=100)
        payment = cash.accounting_transfer_to(vendor.account, Money(5000, "JPY"))
        print(f"From: {payment.legs.last().account}")
        print(f"Balance: {vendor.balance()}")
        print("")
        print("</Dairy Peddler Balance>")
        print("")
        self.assertEqual(vendor.balance(), 0)

    def procurement_lifecycle(self, name, start, end, next, do_pay=True):
        print(f"(make-procurements dairy-peddler {start} - {end})")
        vendor = Vendor.objects.get(name=name)
        make_procurements(vendor, "Milk", Money(500, "JPY"), 1, start)
        legs = (
            Leg.objects.filter(transaction__date__range=(start, end))
            .order_by("id", "transaction__date")
            .filter(account=vendor.account)
        )
        for leg in legs:
            print(
                leg.transaction.date,
                leg.id,
                leg.account,
                leg.account_balance_before(),
                leg.account_balance_after(),
            )
        print(f"{vendor.name}: {vendor.balance()}")

        print("")
        print("(make-invoice)")
        procurements = TransactionDetail.objects.filter(
            summary__legs__account=vendor.account,
            summary__date__range=(start, end),
        )
        invoice = vendor.create_invoice(next, procurements)
        print(f"Amount: {invoice.amount}")
        if do_pay:
            print("")
            print("(make-payment)")
            cash = Account.objects.get(code=100)
            with freeze_time(next):
                payment = cash.accounting_transfer_to(
                    vendor.account, Money(5000, "JPY")
                )
                print(
                    f"From: {payment.date.date()} | {payment.legs.first().id} | {payment.legs.first().account}"
                )
                print(
                    f"To: {payment.date.date()} | {payment.legs.last().id} | {payment.legs.last().account}"
                )
            print("")
        print(f"Balance: {vendor.balance()}")
        print("")

    def make_payment(self, name, amount, date):
        vendor = Vendor.objects.get(name=name)

        print("")
        print("(make-payment)")
        cash = Account.objects.get(code=100)
        payment = cash.accounting_transfer_to(
            vendor.account, Money(amount, "JPY"), date=date
        )
        print(
            f"From: {payment.date.date()} | {payment.legs.first().id} | {payment.legs.first().account}"
        )
        print(
            f"To: {payment.date.date()} | {payment.legs.last().id} | {payment.legs.last().account}"
        )
        print("")

    def test_three_months_procurements_and_payments(self):
        print("")
        print("========== Three Months Procurements and Payments")
        print("")
        self.procurement_lifecycle(
            "Clyde&Jane Dairy Folks", april, end_of_april, may, do_pay=False
        )
        self.procurement_lifecycle("Clyde&Jane Dairy Folks", may, end_of_may, june)
        self.procurement_lifecycle(
            "Clyde&Jane Dairy Folks",
            june,
            end_of_june,
            june.add(months=1),
            do_pay=False,
        )

        cash = Account.objects.get(code=100)
        vendor = Vendor.objects.get(name="Clyde&Jane Dairy Folks")
        balance = vendor.balance()
        invoices = Invoice.objects.filter(vendor=vendor)
        sum_of_amounts = invoices.aggregate(total=Sum("amount"))["total"]
        legs = Leg.objects.filter(account=vendor.account).order_by("transaction__date")
        for leg in legs:
            if leg.account_balance_after() == balance:
                print(
                    f"Last Leg leaving a balance of {balance}: {leg.transaction.id} | {leg.transaction.date} | {leg.account}"
                )
                break

        _date = pendulum.date(2024, 8, 25)
        print(f"Account Balance: {balance}")
        print("")
        # for invoice in invoices:
        #     interval = _date - invoice.due_on
        #     days = interval.in_days()
        #     if days > 0:
        #         print(
        #             f"Before: {invoice.account_balance_before()} | After: {invoice.account_balance_after()}"
        #         )
        #         print(
        #             f"Invoiced for transactions from {invoice.procurements.first().summary.date} to {invoice.procurements.last().summary.date} | {invoice}"
        #         )
        #         print(f"The invoice due date is {invoice.due_on}")
        #         print(f"Today is {_date}, so the invoice is {days} days over due")
        #         print("")
        #     else:
        #         print(
        #             f"Before: {invoice.account_balance_before()} | After: {invoice.account_balance_after()}"
        #         )
        #         print(
        #             f"Invoiced for transactions from {invoice.procurements.first().summary.date} to {invoice.procurements.last().summary.date} | {invoice}"
        #         )
        #         print(f"The invoice due date is {invoice.due_on}")
        #         print(f"Today is {_date}, so the invoice is current.")
        #         print("")

        amount_count = Balance(0, "JPY")

        print("+++++ INVOICES +++++")
        past_due_invoices = []
        all_invoices = []
        print(f"Num of invoices before loop: {invoices.count()}")
        for invoice in invoices.order_by("due_on"):
            all_invoices.append(invoice)
            if balance > amount_count and invoice.days_past_due_date(_date) > 0:
                print(invoice)
                amount_count += Balance([invoice.amount])
                past_due_invoices.append(invoice)
                print(amount_count)
                print(f"invoice is {invoice.days_past_due_date(_date)} past due")
                if invoice.is_1_to_30_days_past_due(_date):
                    print("It's in the 1-30 column")
                if invoice.is_31_to_60_days_past_due(_date):
                    print(f"It's in the 31-60 column")
                if invoice.is_61_to_90_days_past_due(_date):
                    print("It's in the 61-90 column")
                if invoice.is_91_or_more_days_past_due(_date):
                    print("It's really past due.")
                print("")
            else:
                print(f"Invoice is current")
                print(invoice)
                print("")
                break
        print(f"Num of invoices after loop: {len(all_invoices)}")
        print(f"Num of past due invoices: {len(past_due_invoices)}")
