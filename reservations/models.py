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
from phonenumber_field.modelfields import PhoneNumberField

from core.models import Item, ContactInfo, BaseModel
from customer.models import Customer
from reservations.forms import GrillOptionForm

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
    start_date = models.DateField(verbose_name=_("Start"), null=True)
    end_date = models.DateField(verbose_name=_("End"), null=True)
    status_changed = MonitorField(monitor="status")
    type_changed = MonitorField(monitor="stay_type")
    price = models.DecimalField(max_digits=19, decimal_places=4, default=10000.00)

    def get_stay_range(self):
        return (
            self.start_date,
            self.end_date,
        )

    @property
    def price_fully_rounded(self):
        if self.days:
            return round(self.price * self.days, 0)
        else:
            return 0

    @property
    def price_per_day(self):
        return round(self.price, 0)

    @property
    def days(self):
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return delta.days
        else:
            return None

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


class Reservation(BaseModel):
    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True, blank=True)
    stay = models.ForeignKey(Stay, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(
        max_length=50, verbose_name=_("First name"), null=True
    )
    last_name = models.CharField(max_length=50, null=True)
    email = models.EmailField(max_length=254, null=True)
    phone = PhoneNumberField(max_length=254, null=True)
    order_items = models.ManyToManyField(OrderItem)

    def add_order_item(self, item_id):
        item = Item.objects.get(id=item_id)
        order_item = OrderItem.objects.create(item=item)
        self.order_items.add(order_item)

    def remove_order_item(self, item_id):
        order_item = self.order_items.get(item_id=item_id)
        self.order_items.remove(order_item)
        order_item.delete()

    def get_grills(self):
        all_grills = (
            Item.objects.filter(category__name="grill")
            .filter(reservation_option=True)
            .order_by("pk")
        )
        reserved_grills_ids = self.order_items.filter(
            item__category__name="grill", item__reservation_option=True
        ).values_list("item_id", flat=True)
        grills = []
        for grill in all_grills:
            is_reserved = False
            if grill.id in reserved_grills_ids:
                is_reserved = True
            form = GrillOptionForm(initial={"grill_id": grill.id})
            grills.append([grill, form, is_reserved])
        return grills

    def set_dates(self, selected_date: datetime):
        if not self.stay.start_date or selected_date < self.stay.start_date:
            self.stay.start_date = selected_date
            if self.stay.end_date:
                self.stay.end_date = None
        elif self.stay.start_date and not self.stay.end_date:
            self.stay.end_date = selected_date
        elif self.stay.start_date and self.stay.end_date:
            self.stay.start_date = selected_date
            self.stay.end_date = None
        self.stay.save()
        return self.stay.start_date, self.stay.end_date

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
        if self.stay.price:
            total += self.stay.price_fully_rounded
            return total
        else:
            return None

    @property
    def price_fully_rounded(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price_rounded
        total += self.stay.price_fully_rounded
        return round(total, 0)

    @property
    def stay_price(self):
        return self.stay.total_price

    @property
    def start(self):
        return self.stay.start_date

    @property
    def end(self):
        return self.stay.end_date

    def set_status(self, status_choice: str):
        return self.stay.set_status(status_choice)

    def confirm(self):
        self.set_status("reserved")

    def __str__(self):
        return f"Reservation id: {self.id}, User: {self.user}"

    def get_absolute_url(self, pk):
        return reverse("winadmin:reservation_detail", kwargs={"pk": self.pk})


class ReservationToken(models.Model):
    class Meta:
        verbose_name = _("Reservation Token")
        verbose_name_plural = _("Reservation Tokens")

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
