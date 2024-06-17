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
from djmoney.money import Money as DefaultMoney
from hordak import models as accounting_models
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


# class Transaction(BaseModel):
#     class TransactionReturnsManager(models.Manager):
#         def get_queryset(self):
#             return (
#                 super()
#                 .get_queryset()
#                 .filter(name__in=["return"])
#                 .order_by("created_at")
#             )

#         def create_returns_from_order(self, order_obj):
#             with db_transaction.atomic():
#                 orderitem_transactions = []
#                 for orderitem in order_obj.items.all():
#                     orderitem_transaction = self.create(
#                         orderitem_obj=orderitem, customer_obj=order_obj.customer
#                     )
#                     orderitem_transactions.append(orderitem_transaction)
#                 return orderitem_transactions

#         def create(self, orderitem_obj, customer_obj):
#             with db_transaction.atomic():
#                 transaction_obj = self.model.objects.create(
#                     name=Transaction.TransactionType.RETURN,
#                     customer=customer_obj,
#                     product=orderitem_obj.item.name,
#                     quantity=orderitem_obj.quantity,
#                     price_per_unit=orderitem_obj.item.price,
#                     total_price=orderitem_obj.item.price * orderitem_obj.quantity,
#                 )
#             return transaction_obj

#     class TransactionSalesManager(models.Manager):
#         def get_queryset(self):
#             return (
#                 super().get_queryset().filter(name__in=["sale"]).order_by("created_at")
#             )

#         def create_sales_from_order(self, order_obj):
#             with db_transaction.atomic():
#                 orderitem_transactions = []
#                 for orderitem in order_obj.items.all():
#                     orderitem_transaction = self.create(
#                         orderitem_obj=orderitem, customer_obj=order_obj.customer
#                     )
#                     orderitem_transactions.append(orderitem_transaction)
#                 return orderitem_transactions

#         def create(self, orderitem_obj, customer_obj):
#             with db_transaction.atomic():
#                 transaction_obj = self.model.objects.create(
#                     name=Transaction.TransactionType.SALE,
#                     customer=customer_obj,
#                     product=orderitem_obj.item.name,
#                     quantity=orderitem_obj.quantity,
#                     price_per_unit=orderitem_obj.item.price,
#                     total_price=orderitem_obj.item.price * orderitem_obj.quantity,
#                 )
#             return transaction_obj

#     class TransactionReservationsManager(models.Manager):
#         def get_queryset(self):
#             return (
#                 super()
#                 .get_queryset()
#                 .filter(name__in=["sale"])
#                 .filter(product__in=_("Reservation"))
#                 .order_by("created_at")
#             )

#         def create(self, reservation_obj):
#             with db_transaction.atomic():
#                 transaction_obj = self.model.objects.create(
#                     name=Transaction.TransactionType.SALE,
#                     customer=reservation_obj.customer,
#                     product=_("Reservation"),
#                     quantity=reservation_obj.get_stay_period_in_nights(),
#                     price_per_unit=reservation_obj.get_price()
#                     / reservation_obj.get_stay_period_in_nights(),
#                     total_price=reservation_obj.get_price(),
#                 )
#                 return transaction_obj

#     class Meta:
#         verbose_name = _("Transaction")
#         verbose_name_plural = _("Transactions")

#     class TransactionType(models.TextChoices):
#         # 売上、仕入れ、返品、預金振込
#         SALE = "sale", _("Sale")
#         PROCUREMENT = "procurement", _("Procurement")
#         RETURN = "return", _("Return")
#         DEPOSIT = "deposit", _("Deposit")

#     name = models.CharField(
#         max_length=30, choices=TransactionType, verbose_name=_("Name")
#     )
#     customer = models.ForeignKey(
#         Customer,
#         null=True,
#         blank=True,
#         on_delete=models.SET_NULL,
#         verbose_name=_("Customer"),
#     )
#     product = models.CharField(
#         max_length=50, verbose_name=_("Product")
#     )  # For Item, the name. For Reservation, "Reservation"
#     quantity = models.IntegerField(
#         default=1, verbose_name=_("Quantity")
#     )  # For Reservation, number of nights
#     price_per_unit = models.DecimalField(
#         max_digits=19, decimal_places=2, verbose_name=_("Price Per Unit")
#     )  # Price per night
#     total_price = models.DecimalField(
#         max_digits=19, decimal_places=2, verbose_name=_("Price Per Unit")
#     )
#     objects = models.Manager()
#     sales = TransactionSalesManager()
#     returns = TransactionReturnsManager()
#     reservations = TransactionReservationsManager()

#     @property
#     def price_rounded(self):
#         return round(self.item.price, 2)

#     @property
#     def total_price_rounded(self):
#         return round(self.total_price, 2)

#     @property
#     def sale_amount(self):
#         if self.name == "sale":
#             return self.total_price_rounded

#     @property
#     def return_amount(self):
#         if self.name == "return":
#             return self.total_price_rounded

#     @property
#     def purchase_amount(self):
#         if self.name == "purchase":
#             return self.total_price_rounded

#     @property
#     def payment_amount(self):
#         if self.name == "deposit":
#             return self.total_price_rounded

#     def add_total_price(self):
#         total_price = self.quantity * self.price_rounded
#         self.total_price = total_price
#         return self.total_price

#     def __str__(self):
#         return f"{self.name}, {self.total_price_rounded}"

#     def get_absolute_url(self):
#         return reverse("winadmin:transaction_detail", args=[str(self.pk)])


class Vendor(BaseModel):
    class Meta:
        verbose_name = _("Vendor")
        verbose_name_plural = _("Vendors")

    name = models.CharField(max_length=50, verbose_name=_("Name"))
    cutoff_day = models.SmallIntegerField(
        default=30, validators=[MaxValueValidator(31), MinValueValidator(-1)]
    )
    due_day = models.SmallIntegerField(
        default=30, validators=[MaxValueValidator(31), MinValueValidator(-1)]
    )

    def get_cutoff_date(self, invoice_year, invoice_month):
        default_timezone = timezone.get_default_timezone()
        cutoff_day = self.cutoff_day
        is_end_of_month = cutoff_day == -1
        cutoff_date = None
        if is_end_of_month:
            cutoff_date = (
                pendulum.datetime(invoice_year, invoice_month, 1, tz=default_timezone)
                .subtract(months=1)
                .end_of("month")
                .start_of("day")
            )
        else:
            cutoff_date = pendulum.datetime(
                invoice_year, invoice_month, cutoff_day, tz=default_timezone
            ).start_of("day")
        return cutoff_date

    def get_due_date(self, cutoff_date):
        cutoff_day = self.cutoff_day
        cutoff_day_is_end_of_month = cutoff_day == -1
        due_day = self.due_day
        due_day_is_end_of_month = due_day == -1
        due_date = None
        if due_day_is_end_of_month and cutoff_day_is_end_of_month:
            due_date = cutoff_date.add(months=1).end_of("month")
        elif due_day_is_end_of_month and not cutoff_day_is_end_of_month:
            due_date = cutoff_date.end_of("month")
        else:
            due_date = cutoff_date.add(days=due_day)
        return due_date

    def create_invoice(self, _date, procurements):
        cutoff_date = self.get_cutoff_date(_date.year, _date.month)
        due_date = self.get_due_date(cutoff_date)
        amount = 0
        for procurement in procurements:
            amount += procurement.get_total_price()
        invoice = Invoice.objects.create(
            vendor=self, invoiced_on=cutoff_date, due_on=due_date, amount=amount
        )
        for procurement in procurements:
            invoice.procurements.add(procurement)
        invoice.save()
        return invoice

    def get_invoice_period(self, year, month):
        this_month_cutoff_date = self.get_cutoff_date(year, month)
        last_month_cutoff_date = this_month_cutoff_date.subtract(months=1)
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
    procurements = models.ManyToManyField(Procurement)
    invoiced_on = PendulumDateTimeField(verbose_name=_("Invoiced On"))
    due_on = PendulumDateTimeField(verbose_name=_("Due On"))
    amount = models.DecimalField(max_digits=19, decimal_places=2)

    objects = models.Manager()
    current = CurrentInvoiceManager()

    def compare_to_current(self, invoice):
        current = self.current
        diff = current.due_on.diff(invoice.due_on)
        return diff

    def __str__(self):
        return f"Vendor: {self.vendor}, Due On: {self.due_on}"


class TransactionItem(BaseModel):
    class Meta:
        verbose_name = _("Transaction Item")
        verbose_name_plural = _("Transaction Items")

    item = models.CharField(max_length=50, verbose_name=_("Item"))
    quantity = models.PositiveIntegerField(verbose_name=_("Quantity"))
    price_per_unit = MoneyField(
        max_digits=19,
        decimal_places=2,
        default_currency="JPY",
        verbose_name=_("Price Per Unit"),
    )

    def __str__(self):
        return f"{self.item}, {self.price_per_unit}, {self.quantity}"


class TransactionDetail(BaseModel):
    class Meta:
        verbose_name = _("Transaction Detail")
        verbose_name_plural = _("Transaction Details")

    summary = models.ForeignKey(
        accounting_models.Transaction,
        on_delete=models.CASCADE,
        verbose_name=_("Summary"),
    )
    items = models.ManyToManyField(TransactionItem)

    def __str__(self):
        return f"{self.summary.date} - {[item for item in self.items.all()]}"


class Account(accounting_models.Account):
    class Meta:
        verbose_name = _("Account")
        verbose_name_plural = _("Accounts")
