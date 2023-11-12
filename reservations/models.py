import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from model_utils.fields import StatusField, MonitorField

from core.models import Item, ContactInfo, BaseModel
from customer.models import Customer

auth_user = get_user_model()


class OrderItem(BaseModel):
    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"OrderItem_ID: {self.id}, Item_name: {self.item.name}"


class Order(models.Model):
    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True)
    # customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
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


class Address(BaseModel):
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


class StayManager(models.Manager):
    def get_stays_for_date(self, date):
        time_zone = ZoneInfo("Asia/Tokyo")
        target_date = datetime.strptime(date, "%Y-%m-%d").astimezone(time_zone).date()
        next_date = target_date + timedelta(days=1)

        # ex: Stay.objects.get_stays_for_date("2023-09-13")
        # returns all Stays that include the date within the range of their
        # start_datetime and end_datetime.
        return self.filter(
            start_datetime__date__lt=next_date, end_datetime__date__gte=target_date
        )


class Stay(BaseModel):
    class Meta:
        verbose_name = _("Stay")
        verbose_name_plural = _("Stays")

    objects = StayManager()
    STATUS = Choices(
        ("not_reserved", _("Not Reserved")),
        ("reserved", _("Reserved")),
        ("checked_in", _("Checked In")),
        ("checked_out", _("Checked Out")),
        ("cancelled", _("Cancelled")),
    )
    STAY_TYPE_CHOICES = Choices(("hourly", _("Hourly")), ("overnight", _("Overnight")))
    status = StatusField()
    stay_type = models.CharField(
        max_length=255,
        choices=STAY_TYPE_CHOICES,
        default=STAY_TYPE_CHOICES.hourly,
    )
    start_datetime = models.DateTimeField(default=timezone.now, verbose_name=_("Start"))
    end_datetime = models.DateTimeField(default=timezone.now, verbose_name=_("End"))
    status_changed = MonitorField(monitor="status")
    type_changed = MonitorField(monitor="stay_type")
    price = models.DecimalField(max_digits=19, decimal_places=4, default=10000.00)

    def get_stay_range(self):
        return (
            self.start_datetime.strftime("%Y-%m-%d %H:%S"),
            self.end_datetime.strftime("%Y-%m-%d %H:%S"),
        )

    @property
    def price_fully_rounded(self):
        return round(self.price * self.days, 0)

    @property
    def price_per_day(self):
        return round(self.price, 0)

    @property
    def days(self):
        delta = self.end_datetime - self.start_datetime
        return delta.days

    @property
    def total_price(self):
        stay_days = self.days
        total_price = stay_days * self.price_fully_rounded
        return total_price

    @property
    def status_display(self):
        return Stay.STATUS[self.status]

    def __str__(self):
        start, end = self.get_stay_range()
        return f"ID: {self.id}, {_('Start')}: {start} {_('End')}: {end}"

    def set_status(self, status_choice):
        new_status = getattr(self.STATUS, status_choice, None)
        if new_status is not None:
            self.status = new_status
            self.save()
            return new_status
        else:
            raise ValueError(f"{_('Invalid status choice')}: {status_choice}")


class Reservation(models.Model):
    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True, blank=True)
    stay = models.ForeignKey(Stay, on_delete=models.CASCADE, null=True, blank=True)
    contact_info = models.ForeignKey(
        ContactInfo, on_delete=models.CASCADE, null=True, blank=True
    )
    order_items = models.ManyToManyField(OrderItem)
    updated_datetime = models.DateTimeField(auto_now=True)

    def add_order_item(self, item_pk):
        item = Item.objects.get(pk=item_pk)
        order_item = OrderItem.objects.create(item=item)
        self.order_items.add(order_item)

    def remove_order_item(self, item_pk):
        item = Item.objects.get(pk=item_pk)
        order_item = OrderItem.objects.get(item=item)
        self.order_items.remove(order_item)

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
        total += self.stay.price_fully_rounded
        return total

    @property
    def price_fully_rounded(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price_rounded
        total += self.stay.price_fully_rounded
        return round(total, 0)

    def set_status(self, status_choice: str):
        return self.stay.set_status(status_choice)

    def __str__(self):
        return f"Reservation id: {self.id}, User: {self.user}"

    def get_absolute_url(self, pk):
        return reverse("winadmin:edit_reservation", kwargs={"pk": self.pk})


class ReservationToken(models.Model):
    class Meta:
        verbose_name = _("Reservation Token")
        verbose_name_plural = _("Reservation Tokens")

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
