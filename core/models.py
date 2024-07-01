import datetime

import pendulum
from customer.models import Customer
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db import transaction as db_transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from djmoney.money import Money as DefaultMoney
from hordak import models as accounting_models
from hordak.models import Leg
from hordak.utilities.currency import Balance
from phonenumber_field.modelfields import PhoneNumberField
from winvillage import settings

auth_user = get_user_model()


class PendulumDateTimeField(models.DateTimeField):
    # https://docs.djangoproject.com/en/5.0/howto/custom-model-fields#converting-values-to-python-objects
    # If present for the field subclass, from_db_value() will be called in all circumstances when
    # the data is loaded from the database, including in aggregates and values() calls.
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            if settings.USE_TZ:
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return pendulum.instance(value)
        return pendulum.parse(value)

    # https://docs.djangoproject.com/en/5.0/howto/custom-model-fields#converting-values-to-python-objects
    # to_python() is called by deserialization and during the clean() method used from forms.

    # As a general rule, to_python() should deal gracefully with any of the following arguments:
    # -- An instance of the correct type
    # -- A string
    # -- None (if the field allows null=True)
    def to_python(self, value):
        if isinstance(value, pendulum.DateTime):
            return value
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        if value is None:
            return value
        return pendulum.parse(value)

    def get_prep_value(self, value):
        if isinstance(value, pendulum.DateTime):
            return value.to_iso8601_string()
            # return value
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        if isinstance(value, datetime.date):
            return pendulum.instance(value)
        if value is None:
            return value

    # def value_to_string(self, obj):
    #     value = self._get_val_from_obj(obj)
    #     return "" if value is None else value.isoformat()

    def db_type(self, connection):
        if connection.vendor == "mysql":
            return "datetime"
        else:
            return "timestamp"


class BaseModel(models.Model):
    created_at = PendulumDateTimeField(auto_now_add=True, null=True)
    updated_at = PendulumDateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class Setting(BaseModel):
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} - {self.value}"


class ContactInfo(BaseModel):
    class Meta:
        verbose_name = _("Contact Info")
        verbose_name_plural = _("Contact Infos")

    first_name = models.CharField(max_length=50, verbose_name=_("First name"))
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)
    phone = PhoneNumberField(max_length=254)

    def __str__(self):
        return f"{self.first_name}, {self.last_name}, {self.email}"


class Category(BaseModel):
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    name = models.CharField(max_length=100, verbose_name=_("Category Name"))

    def __str__(self):
        return f"{self.name}"


class Item(BaseModel):
    class InStockItemManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(stock_quantity__gt=0)

        # We add a "quantity_in_order" field to make the occupant purchase view easier to set up.
        def with_orderitem_quantities(self, order_obj):
            return self.annotate(
                quantity_in_order=Coalesce(
                    Sum(
                        "orderitem__quantity",
                        filter=Q(orderitem__order=order_obj),
                        distinct=True,
                    ),
                    0,
                )
            )

    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")

    name = models.CharField(verbose_name=_("Name"), max_length=100, unique=True)
    price = MoneyField(
        max_digits=19, decimal_places=2, default_currency="JPY", verbose_name=_("Price")
    )
    category = models.ForeignKey(
        Category,
        verbose_name=_("Category"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    image = models.ImageField(
        upload_to="item_images/", verbose_name=_("Image"), null=True, blank=True
    )
    stock_quantity = models.IntegerField(default=1, verbose_name=_("Stock Quantity"))
    active = models.BooleanField(default=False, verbose_name=_("Active?"))
    reservation_option = models.BooleanField(
        default=False, verbose_name=_("Reservation Option?")
    )
    description = models.TextField(
        default=_("Long description"), verbose_name=_("Description"), null=True
    )
    short_description = models.CharField(
        max_length=280,
        default=_("Short description"),
        verbose_name=_("Short Description"),
        null=True,
    )
    objects = models.Manager()
    in_stock = InStockItemManager()

    @property
    def price_rounded(self):
        return round(self.price, 2)

    @property
    def price_fully_rounded(self):
        return round(self.price, 0)

    def get_stock_value(self):
        return self.price_rounded * self.stock_quantity

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("winadmin:item_detail", args=[str(self.pk)])


def get_account(code):
    return accounting_models.Account.objects.get(code=code)


def get_sales_account_from_configuration(code=300):
    account = get_account(code=code)
    assert account.type == "IN"
    return account


def get_cash_account_from_configuration(code=100):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_accounts_receivable_account_from_configuration(code=110):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_inventory_account_from_configuration(code=120):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_cogs_account_from_configuration(code=400):
    account = get_account(code=code)
    assert account.type == "EX"
    return account


def get_accounts_payable_account_from_configuration(code=200):
    account = get_account(code=code)
    assert account.type == "LI"
    return account


class Vendor(BaseModel):
    class Meta:
        verbose_name = _("Vendor")
        verbose_name_plural = _("Vendors")

    class VendorManager(models.Manager):
        def create(self, *args, **kwargs):
            accounts_payable = get_accounts_payable_account_from_configuration()
            vendor_accounts = accounting_models.Account.objects.filter(
                parent=accounts_payable
            )
            name = kwargs.get("name")
            if name is None:
                raise ValueError("A name must be provided for a Vendor.")
            account = accounting_models.Account.objects.create(
                name=name,
                type="LI",
                parent=accounts_payable,
                code=vendor_accounts.count() + 1,
            )
            vendor = self.model(*args, **kwargs)
            vendor.account = account
            vendor.save()
            return vendor

    account = models.ForeignKey(
        accounting_models.Account,
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    cutoff_day = models.SmallIntegerField(
        default=30,
        validators=[MaxValueValidator(31), MinValueValidator(-1)],
        verbose_name=_("Cutoff Day"),
    )
    due_day = models.SmallIntegerField(
        default=30,
        validators=[MaxValueValidator(31), MinValueValidator(-1)],
        verbose_name=_("Due Day"),
    )
    phone = PhoneNumberField(null=True, verbose_name=_("Phone"))
    postal_code = models.CharField(
        max_length=255, null=True, verbose_name=_("Postal Code")
    )
    address = models.CharField(max_length=255, null=True, verbose_name=_("Address"))
    city = models.CharField(max_length=255, null=True, verbose_name=_("City"))
    prefecture = models.CharField(
        max_length=255, null=True, verbose_name=_("Prefecture")
    )

    objects = VendorManager()

    def get_cutoff_date(self, _date):
        invoice_year = _date.year
        invoice_month = _date.month
        default_timezone = timezone.get_default_timezone()
        cutoff_day = self.cutoff_day
        is_end_of_month = cutoff_day == -1
        cutoff_date = None
        if is_end_of_month:
            cutoff_date = (
                pendulum.date(invoice_year, invoice_month, 1)
                .end_of("month")
                .start_of("day")
            )
        else:
            cutoff_date = pendulum.date(
                invoice_year, invoice_month, cutoff_day
            ).start_of("day")
        return cutoff_date

    def get_due_date(self, cutoff_date):
        cutoff_day = self.cutoff_day
        cutoff_day_is_end_of_month = cutoff_day == -1
        due_day = self.due_day
        due_day_is_end_of_month = due_day == -1
        due_date = None
        if due_day_is_end_of_month and cutoff_day_is_end_of_month:
            due_date = cutoff_date.add(months=1).end_of("month").start_of("day")
        elif due_day_is_end_of_month and not cutoff_day_is_end_of_month:
            due_date = cutoff_date.end_of("month").start_of("day")
        else:
            due_date = cutoff_date.add(days=due_day)
        return due_date

    def create_invoice(self, _date, procurements):
        cutoff_date = self.get_cutoff_date(_date)
        due_date = self.get_due_date(cutoff_date)
        amount = 0
        for procurement in procurements:
            total = procurement.total()
            amount += total
        invoice, _ = Invoice.objects.get_or_create(
            vendor=self, invoiced_on=cutoff_date, due_on=due_date, amount=amount
        )
        for procurement in procurements:
            invoice.procurements.add(procurement)
        invoice.save()
        return invoice

    def get_invoice_period(self, _date):
        this_month_cutoff_date = self.get_cutoff_date(_date)
        last_month_cutoff_date = self.get_cutoff_date(_date.subtract(months=1))
        return {"start": last_month_cutoff_date, "end": this_month_cutoff_date}

    def get_current_invoice(self):
        invoice = Invoice.current.filter(vendor=self)
        if invoice.exists():
            return invoice.first()
        return invoice

    def get_one_to_thirty_day_past_due_invoice(self):
        today = pendulum.today(tz=timezone.get_default_timezone_name())
        current_invoice = self.get_current_invoice()
        current_due_date = current_invoice.due_on

    def balance(self):
        return self.account.balance()

    def __str__(self):
        return self.name


class Procurement(BaseModel):
    class Meta:
        verbose_name = _("Procurement")
        verbose_name_plural = _("Procurements")

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    price_per_unit = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name=_("Price")
    )
    quantity = models.PositiveSmallIntegerField(verbose_name=_("Quantity"))
    procured_on = PendulumDateTimeField(verbose_name=_("Procured On"))

    def get_total_price(self):
        return self.price_per_unit * self.quantity

    def __str__(self):
        return f"{self.vendor}, {self.product}"


class Invoice(BaseModel):
    class CurrentInvoiceManager(models.Manager):
        def get_queryset(self):
            today = pendulum.today(tz=timezone.get_current_timezone_name())
            return super().get_queryset().filter(due_on__gte=today)

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    procurements = models.ManyToManyField("TransactionDetail")
    invoiced_on = PendulumDateTimeField(verbose_name=_("Invoiced On"))
    due_on = PendulumDateTimeField(verbose_name=_("Due On"))
    amount = MoneyField(
        max_digits=19,
        decimal_places=2,
        default_currency="JPY",
        verbose_name=_("Price Per Unit"),
    )

    objects = models.Manager()
    current = CurrentInvoiceManager()

    def compare_to_current(self, invoice):
        current = self.current
        diff = current.due_on.diff(invoice.due_on)
        return diff

    def account_balance_before(self):
        if self.procurements.exists():
            first = self.procurements.first().summary
            before = first.legs.get(account=self.vendor.account)
            return before.account_balance_before()
        else:
            return Balance(0, "JPY")

    def account_balance_after(self):
        if self.procurements.exists():
            first = self.procurements.last().summary
            before = first.legs.get(account=self.vendor.account)
            return before.account_balance_after()
        else:
            return Balance(0, "JPY")

    def days_past_due_date(self, _date=None):
        if _date is None:
            _date = pendulum.now().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return days

    def is_current(self, _date=None):
        if _date is None:
            _date = pendulum.now().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return days > 0

    def is_1_to_30_days_past_due(self, _date=None):
        if _date is None:
            _date = pendulum.today().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return 30 >= days >= 1

    def is_31_to_60_days_past_due(self, _date=None):
        if _date is None:
            _date = pendulum.now().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return 60 >= days >= 31

    def is_61_to_90_days_past_due(self, _date=None):
        if _date is None:
            _date = pendulum.now().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return 90 >= days >= 61

    def is_91_or_more_days_past_due(self, _date=None):
        if _date is None:
            _date = pendulum.now().date()
        interval = _date - self.due_on.date()
        days = interval.in_days()
        return days >= 91

    def __str__(self):
        return f"ID: {self.id} | {self.vendor} | {self.amount} | Inv: {self.invoiced_on.date()} | Due: {self.due_on.date()}"


class TransactionDetail(BaseModel):
    class SaleTransactionDetailManager(models.Manager):
        def get_queryset(self):
            from core.accounting_utils import get_sales_account_from_configuration

            account = get_sales_account_from_configuration()
            legs = Leg.objects.filter(account=account)
            return super().get_queryset().filter(summary__legs__in=legs)

        def create(self, to_account, amount, item, quantity, price_per_unit):
            from core.accounting_utils import get_sales_account_from_configuration

            if not isinstance(amount, Money):
                amount = Money(amount, "JPY")
            with db_transaction.atomic():
                sales_account = get_sales_account_from_configuration()
                transaction = sales_account.accounting_transfer_to(to_account, amount)
                detail = super().create(
                    summary=transaction,
                    item=item,
                    quantity=quantity,
                    price_per_unit=price_per_unit,
                )
                return detail

    class TypeChoices(models.TextChoices):
        SALE = "SA", _("Sale")
        PROCUREMENT = "PR", _("Procurement")
        PAYMENT = "PA", _("Payment")

    class Meta:
        verbose_name = _("Transaction Detail")
        verbose_name_plural = _("Transaction Details")

    summary = models.ForeignKey(
        accounting_models.Transaction,
        on_delete=models.CASCADE,
        verbose_name=_("Summary"),
    )
    item = models.CharField(max_length=50, verbose_name=_("Item"))
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))
    price_per_unit = MoneyField(
        default=0,
        max_digits=19,
        decimal_places=2,
        default_currency="JPY",
        verbose_name=_("Price Per Unit"),
    )
    type = models.CharField(choices=TypeChoices, max_length=20, verbose_name=_("Type"))
    objects = models.Manager()
    sales = SaleTransactionDetailManager()

    def to_account(self):
        account = None
        for leg in self.summary.legs.all():
            if leg.is_debit():
                return leg.account.name

    def from_account(self):
        account = None
        for leg in self.summary.legs.all():
            if leg.is_credit():
                return leg.account.name

    def account_balance_after_payment(self, vendor):
        account = vendor.account
        detail = self.objects.filter(type="PA", summary__legs__account=account).latest(
            "summary__date"
        )

    def total(self):
        return self.quantity * self.price_per_unit


class Account(accounting_models.Account):
    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
