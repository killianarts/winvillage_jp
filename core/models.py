import datetime

import pendulum
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from phonenumber_field.modelfields import PhoneNumberField

from customer.models import Customer

auth_user = get_user_model()


class PendulumDateTimeField(models.DateTimeField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        return pendulum.parse(value)

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
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        if isinstance(value, datetime.date):
            return pendulum.instance(value)
        if value is None:
            return value

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


class Item(models.Model):
    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")

    name = models.CharField(verbose_name=_("Name"), max_length=100)
    price = models.DecimalField(
        verbose_name=_("Price"), max_digits=19, decimal_places=4
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
    in_stock = models.BooleanField(default=True, verbose_name=_("In Stock?"))
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

    @property
    def price_rounded(self):
        return round(self.price, 2)

    @property
    def price_fully_rounded(self):
        return round(self.price, 0)

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return reverse("winadmin:item_detail", args=[str(self.pk)])


class TransactionSalesManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(name__in=["sale", "purchase", "deposit", "return"])
            .order_by("transaction_datetime")
        )


class Transaction(BaseModel):
    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    NAME_CHOICES = Choices(
        ("sale", _("Sale")),
        ("purchase", _("Purchase")),
        ("return", _("Return")),
        ("deposit", _("Bank Deposit")),
    )
    name = models.CharField(
        max_length=30, choices=NAME_CHOICES, verbose_name=_("Name")
    )  # 売上、仕入れ、返品、預金振込
    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Customer"),
    )
    transaction_datetime = models.DateTimeField(
        default=timezone.now, verbose_name=_("Transaction Datetime")
    )
    item = models.ForeignKey(
        Item, null=False, on_delete=models.CASCADE, verbose_name=_("Item")
    )
    quantity = models.IntegerField(default=1, verbose_name=_("Quantity"))
    total_price = models.DecimalField(
        max_digits=19, decimal_places=4, verbose_name=_("Total Price")
    )
    objects = models.Manager()
    sales = TransactionSalesManager()

    @property
    def price_rounded(self):
        return round(self.item.price, 2)

    @property
    def total_price_rounded(self):
        return round(self.total_price, 2)

    @property
    def sale_amount(self):
        if self.name == "sale":
            return self.total_price_rounded

    @property
    def return_amount(self):
        if self.name == "return":
            return self.total_price_rounded

    @property
    def purchase_amount(self):
        if self.name == "purchase":
            return self.total_price_rounded

    @property
    def payment_amount(self):
        if self.name == "deposit":
            return self.total_price_rounded

    def add_total_price(self):
        total_price = self.quantity * self.price_rounded
        self.total_price = total_price
        return self.total_price

    def __str__(self):
        return f"{self.name}, {self.total_price_rounded}"

    def get_absolute_url(self):
        return reverse("winadmin:transaction_detail", args=[str(self.pk)])
