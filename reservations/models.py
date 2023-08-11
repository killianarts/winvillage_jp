import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from model_utils import Choices
from model_utils.fields import StatusField, MonitorField

auth_user = get_user_model()


class Category(models.Model):
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    title = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.pk}, {self.title}"


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
    description = models.TextField(default=_("Long description"), null=True)
    short_description = models.CharField(
        max_length=280, default=_("Short description"), null=True
    )

    @property
    def price_rounded(self):
        return round(self.price, 2)

    def __str__(self):
        return f"{self.name}"

    def get_absolute_url(self):
        return "/item/%i/" % self.id


class OrderItem(models.Model):
    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.item.name}"


class Order(models.Model):
    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True)
    items = models.ManyToManyField(OrderItem)
    ordered = models.BooleanField(default=False)
    ordered_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"User: {self.user}, Items: {self.get_quantity()}"

    def get_quantity(self):
        order_items = self.items.all()
        quantity = 0
        for item in order_items:
            quantity += item.quantity
        return quantity

    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.item.price * order_item.quantity
        return int(total)


class Address(models.Model):
    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    street_address = models.CharField(max_length=50)
    secondary_address = models.CharField(max_length=100, blank=True)
    postal_code = models.IntegerField()
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.street_address}"

    @property
    def full_address(self):
        address_parts = [self.street_address]

        if self.secondary_address:
            address_parts.append(self.secondary_address)

        address_parts.append(f"{self.city}, {self.state} {self.postal_code}")

        return "\n".join(address_parts)

    def save(self, *args, **kwargs):
        # If this is a new address and is_primary is True, make sure no other addresses
        # for this account have is_primary set to True
        if self.pk is None and self.is_primary:
            Address.objects.filter(user=self.user, is_primary=True).update(
                is_primary=False
            )

        # If this is an existing address and is_primary is being set to True,
        # make sure no other addresses for this account have is_primary set to True
        elif self.pk is not None and self.is_primary:
            Address.objects.filter(user=self.user).exclude(pk=self.pk).update(
                is_primary=False
            )

        super(Address, self).save(*args, **kwargs)


# class Product(models.Model):
#     reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
#     amount = models.FloatField()
#     amount_field = models.CharField(max_length=150)
#     borrowed = models.BooleanField(default=False)
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveIntegerField()
#     content_object = GenericForeignKey("content_type", "object_id")
#
#     @property
#     def available_amount(self):
#         return getattr(self.content_object, self.amount_field)
#
#     @property
#     def amount_without_this_product(self):
#         amount_now = self.available_amount
#         return amount_now - self.amount
#
#     def __str__(self):
#         return "%.2f ) %s" % (self.amount, self.content_object)


class Room(models.Model):
    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")

    name = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return self.name


# class Grill(models.Model):
#     class GrillManager(models.Manager):
#         def get_queryset(self):
#             return super().get_queryset().filter(featured=True)
#
#     objects = models.Manager()
#     featured_grills = GrillManager()
#     price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
#     name = models.CharField(max_length=50)
#     description = models.TextField()
#     featured = models.BooleanField(
#         default=False,
#         verbose_name=_("Featured"),
#         help_text=_(
#             "Featured grills are presented as reservation options during the reservation creation process."
#         ),
#     )
#     model_number = models.CharField(max_length=50, default="MKJ12345")
#     maker = models.CharField(max_length=50, default=_("Default Maker"))
#
#     def __str__(self):
#         return self.name
#
#
# class Food(models.Model):
#     class FoodManager(models.Manager):
#         def get_queryset(self):
#             return super().get_queryset().filter(featured=True)
#
#     objects = models.Manager()
#     featured_foods = FoodManager()
#     price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
#     name = models.CharField(max_length=50)
#     description = models.TextField()
#     featured = models.BooleanField(
#         default=False,
#         verbose_name=_("Featured"),
#         help_text=_(
#             "Featured foods are presented as reservation options during the reservation creation process."
#         ),
#     )
#
#     def __str__(self):
#         return self.name


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


class Stay(models.Model):
    STATUS = Choices(
        ("not_reserved", _("Not Reserved")),
        ("reserved", _("Reserved")),
        ("checked_in", _("Checked In")),
        ("checked_out", _("Checked Out")),
        ("cancelled", _("Cancelled")),
    )
    TYPE_OF_STAY_CHOICES = Choices(
        ("hourly", _("Hourly")), ("overnight", _("Overnight"))
    )
    status = StatusField()
    type = models.CharField(
        max_length=255,
        choices=TYPE_OF_STAY_CHOICES,
        default=TYPE_OF_STAY_CHOICES.hourly,
    )
    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(default=timezone.now)
    status_changed = MonitorField(monitor="status")
    type_changed = MonitorField(monitor="type")
    updated_datetime = models.DateTimeField(auto_now=True)
    price = models.DecimalField(max_digits=19, decimal_places=4, default=10000.00)

    def get_stay_range(self):
        return (
            self.start_datetime.strftime("%Y-%m-%d %H:%S"),
            self.end_datetime.strftime("%Y-%m-%d %H:%S"),
        )

    @property
    def price_rounded(self):
        return round(self.price * self.days, 2)

    @property
    def days(self):
        delta = self.end_datetime - self.start_datetime
        return delta.days

    @property
    def total_price(self):
        stay_days = self.days
        total_price = stay_days * self.price_rounded
        return total_price

    def __str__(self):
        start, end = self.get_stay_range()
        return f"ID: {self.id}, {_('From')}: {start} {_('To')}: {end}"


class Reservation(models.Model):
    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True, blank=True)
    stay = models.ForeignKey(Stay, on_delete=models.CASCADE, null=True, blank=True)
    contact_info = models.ForeignKey(
        ContactInfo, on_delete=models.CASCADE, null=True, blank=True
    )
    order_items = models.ManyToManyField(OrderItem)
    updated_datetime = models.DateTimeField(auto_now=True)

    @property
    def price(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price
        total += self.stay.total_price
        return total

    @property
    def price_rounded(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price_rounded
        total += self.stay.price_rounded
        return total

    @property
    def price_fully_rounded(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price_rounded
        total += self.stay.price_rounded
        return round(total, 0)

    # @property
    # def price_

    def __str__(self):
        return f"Reservation id: {self.id}, Stay id: {self.stay.id}, User: {self.user}"


class ReservationToken(models.Model):
    class Meta:
        verbose_name = _("Reservation Token")
        verbose_name_plural = _("Reservation Tokens")

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
