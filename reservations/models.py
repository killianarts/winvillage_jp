import math
import uuid
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import pendulum
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from model_utils import Choices
from model_utils.fields import StatusField, MonitorField
from phonenumber_field.modelfields import PhoneNumberField

from core.models import Item, ContactInfo, BaseModel, PendulumDateTimeField
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


class SpecialDate(models.Model):
    date = models.DateField()
    name = models.CharField(max_length=255)
    price_per_night = models.DecimalField(max_digits=19, decimal_places=4)
    price_per_hour = models.DecimalField(max_digits=19, decimal_places=4)

    def __str__(self):
        return self.name


# class StayTypes(models.Model):
#     class TypeChoices(models.TextChoices):
#         ROOM = "room", _("Room")
#         BATH = "bath", _("Bath")
#
#     name = models.CharField(max_length=4, choices=TypeChoices, default=TypeChoices.ROOM)
#     # Price is determined both by date and type of the stay
#
#     def __str__(self):
#         return self.name
# models.py


class DefaultPrice(models.Model):
    adult_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    adult_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    child_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    child_price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Adults: {self.adult_price_per_night}/night, {self.adult_price_per_hour}/hour. Children: {self.child_price_per_night}/night, {self.child_price_per_hour}/hour."

    def save(self, *args, **kwargs):
        # Ensure only one instance of DefaultPrice exists in the database
        if not self.pk and DefaultPrice.objects.exists():
            raise ValueError(
                "There can be only one instance of DefaultPrice in the database."
            )
        super().save(*args, **kwargs)


class PricingTier(models.Model):
    class PricingTierManager(models.Manager):
        def order_by_name(self):
            return self.order_by("price_per_night").all()

    objects = PricingTierManager()
    name = models.CharField(max_length=50)

    class NumberOfAdultChoices(models.IntegerChoices):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5
        SIX = 6

    number_of_adults = models.IntegerField(
        default=NumberOfAdultChoices.ONE, choices=NumberOfAdultChoices
    )
    price_per_night = models.DecimalField(max_digits=19, decimal_places=4)
    price_per_hour = models.DecimalField(max_digits=19, decimal_places=4)

    def __str__(self):
        return f"{self.name} {self.price_per_night}/night, {self.price_per_hour}/hour"

    def get_price_per_night(self):
        return round(self.price_per_night, 2)

    def get_price_per_hour(self):
        return round(self.price_per_hour, 2)

    def get_absolute_url(self):
        return reverse("winadmin:pricing_tier_detail", kwargs={"pk": self.pk})


class Room(models.Model):
    name = models.CharField(max_length=50)
    pricing_tiers = models.ManyToManyField(PricingTier)

    def __str__(self):
        return f"Room: {self.name}"


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

    class NumberOfAdultChoices(models.IntegerChoices):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5
        SIX = 6

    class NumberOfChildChoices(models.IntegerChoices):
        ZERO = 0
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5
        SIX = 6

    number_of_adults = models.IntegerField(
        default=NumberOfAdultChoices.ONE, choices=NumberOfAdultChoices
    )
    number_of_children = models.IntegerField(
        default=NumberOfChildChoices.ZERO, choices=NumberOfChildChoices
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    start = PendulumDateTimeField(verbose_name=_("Start"), null=True)
    end = PendulumDateTimeField(verbose_name=_("End"), null=True)
    status_changed = MonitorField(monitor="status")
    type_changed = MonitorField(monitor="stay_type")

    def get_stay_range(self):
        return (
            self.start,
            self.end,
        )

    def is_hourly(self):
        return self.end.date == self.start.date

    def is_weekend(self, date_: datetime.date) -> bool:
        return date_.weekday() > 4

    def is_special_date(self, date_: datetime.date) -> bool:
        return SpecialDate.objects.filter(date=date_).exists()

    def calculate_hourly_price(self):
        total_price = 0
        current_datetime = self.start
        end_datetime = self.end
        while current_datetime < end_datetime:
            if self.is_special_date(current_datetime.date):
                total_price += SpecialDate.objects.get(
                    date=current_datetime.date
                ).price_per_hour
            elif self.is_weekend(current_datetime.date):
                total_price += DefaultPrice.objects.first().weekend_price_per_hour
            else:
                total_price += DefaultPrice.objects.first().price_per_hour
            current_datetime += timedelta(hours=1)
        return total_price

    def calculate_nightly_price(self):
        current_dt = self.start
        pricing_tier = self.room.pricing_tiers.filter(
            number_of_adults=self.number_of_adults
        )
        total_price = 0
        while current_dt.day <= self.end.day:
            total_price += pricing_tier.price_per_night
            current_dt.add(days=1)
        return total_price

    def calculate_price(self):
        total_price = 0
        if self.is_hourly():
            total_price = self.calculate_hourly_price()
        else:
            total_price = self.calculate_nightly_price()
        return round(total_price, 0)

    def days(self):
        if self.start.date and self.end.date:
            delta = self.end.date - self.start.date
            return delta.days
        else:
            return None

    def time_span(self):
        start_datetime = pendulum.instance(self.start)
        end_datetime = pendulum.instance(self.end)
        span = end_datetime.diff(start_datetime)
        return span

    def period_start(self):
        return math.ceil(self.start.time().hour)

    def period_end(self):
        # round(2.5) == 2...
        return math.ceil(self.time_span.in_minutes() / 60)

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

    def set_dates(self, selected_datetime: pendulum.DateTime):
        if not self.stay.start or not self.stay.end:
            self.stay.start = selected_datetime
            self.stay.end = selected_datetime

        START_AND_END_ARE_THE_SAME = self.stay.start == self.stay.end
        NEW_DATE_AFTER_END = selected_datetime > self.stay.end

        if NEW_DATE_AFTER_END and START_AND_END_ARE_THE_SAME:
            self.stay.end = selected_datetime
        else:
            self.stay.start = selected_datetime
            self.stay.end = selected_datetime
        self.stay.save()
        return self.stay.start, self.stay.end

    def check_availability(self, date_):
        tzinfo = timezone.get_current_timezone()
        datetime_with_tz = timezone.make_aware(
            datetime.combine(date_, time.min), tzinfo
        )

        reservations_count = self.objects.filter(
            stay__start__lte=datetime_with_tz,
            stay__end__gte=datetime_with_tz,
            stay__status="reserved",
        ).count()
        return reservations_count < 4

    @property
    def price(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price
        total += self.stay.price
        return round(total, 0)

    @property
    def price_fully_rounded(self):
        total = 0
        for order_item in self.order_items.all():
            total += order_item.item.price_rounded
        total += self.stay.price_fully_rounded
        return round(total, 0)

    def start_time(self):
        if self.stay.start:
            return self.stay.start.time()
        return None

    def end_time(self):
        if self.stay.end:
            return self.stay.end.time()
        return None

    def set_times(self, start_time: time, end_time: time):
        self.stay.start_time = start_time
        self.stay.end_time = end_time
        self.stay.save()
        return self.stay.start_time, self.stay.end_time

    def set_status(self, status_choice: str):
        return self.stay.set_status(status_choice)

    def confirm(self):
        self.set_status("reserved")

    def __str__(self):
        return f"Reservation id: {self.id}, User: {self.user}"

    def order_items_list(self):
        items = []
        for item in self.order_items.all():
            items.append(item)
        return items

    def get_absolute_url(self, pk):
        return reverse("winadmin:reservation_detail", kwargs={"pk": self.pk})


class ReservationToken(models.Model):
    class Meta:
        verbose_name = _("Reservation Token")
        verbose_name_plural = _("Reservation Tokens")

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
