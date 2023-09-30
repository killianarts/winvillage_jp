from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from model_utils import Choices

auth_user = get_user_model()


class ContactInfo(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=254)

    def __str__(self):
        return f"{self.first_name}, {self.last_name}, {self.email}"


class Customer(models.Model):
    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    contact_info = models.ForeignKey(ContactInfo, on_delete=models.CASCADE, null=True)
    user = models.OneToOneField(auth_user, on_delete=models.CASCADE, null=True)
    # square_customer_id = models.CharField(max_length=100, null=True, blank=True)
    # first_name = models.CharField(max_length=100, null=True)
    # last_name = models.CharField(max_length=100, null=True)

    def __str__(self):
        return f"{self.contact_info.first_name} {self.contact_info.last_name}"

    #
    # def get_primary_address(self):
    #     return self.user.address_set.get(is_primary=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Category(models.Model):
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.title}"


class Item(models.Model):
    class Meta:
        verbose_name = _("Item")
        verbose_name_plural = _("Items")

    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=19, decimal_places=4)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL
    )
    image = models.ImageField(upload_to="item_images/", null=True, blank=True)
    stock_quantity = models.IntegerField(default=1)
    in_stock = models.BooleanField(default=True)
    active = models.BooleanField(default=False)
    reservation_option = models.BooleanField(default=False)
    description = models.TextField(default=_("Long description"), null=True)
    short_description = models.CharField(
        max_length=280, default=_("Short description"), null=True
    )

    @property
    def price_rounded(self):
        return round(self.price, 2)

    @property
    def price_fully_rounded(self):
        return round(self.price, 0)

    def __str__(self):
        return f"ID: {self.pk}, Name: {self.name}"

    def get_absolute_url(self):
        return reverse("winadmin:edit_inventory_item", args=[str(self.pk)])


class Transaction(models.Model):
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
        return f"{self.transaction_datetime.strftime('%Y-%m-%d')}, {self.item}, {self.quantity}, {self.total_price}"

    def get_absolute_url(self):
        return reverse("winadmin:edit_transaction", args=[str(self.pk)])
