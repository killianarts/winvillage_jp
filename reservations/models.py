import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pendulum
from core.models import BaseModel, ContactInfo, Item, PendulumDateTimeField
from customer.models import Customer
from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField
from djmoney.money import Money
from hordak import models as accounting_models
from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from recurrence.fields import RecurrenceField
from winvillage.settings import TIME_ZONE

# from reservations.forms import GrillOptionForm

auth_user = get_user_model()


class OrderItem(BaseModel):
    class Meta:
        verbose_name = _("Order Item")
        verbose_name_plural = _("Order Items")

    user = models.ForeignKey(
        auth_user, on_delete=models.CASCADE, null=True, verbose_name=_("User")
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True)
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))

    def __str__(self):
        return f"OrderItem_ID: {self.id}, Item_name: {self.item.name}"


class Order(BaseModel):
    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    user = models.ForeignKey(
        auth_user, on_delete=models.CASCADE, null=True, verbose_name=_("User")
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    items = models.ManyToManyField(OrderItem)
    ordered = models.BooleanField(default=False, verbose_name=_("Ordered?"))

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
        return total

    def make_purchase(self):
        self.ordered = True
        for orderitem in self.items:
            orderitem.item.stock_quantity = (
                orderitem.item.stock_quantity - orderitem.quantity
            )


class Campaign(BaseModel):
    class Meta:
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    name = models.CharField(max_length=50, verbose_name=_("Name"), unique=True)
    recurrences = RecurrenceField(verbose_name=_("Recurrences"), include_dtstart=False)

    def __str__(self):
        return self.name


class PricingTier(BaseModel):
    class Meta:
        verbose_name = _("Pricing tier")
        verbose_name_plural = _("Pricing tiers")

    class PricingTierManager(models.Manager):
        def order_by_name(self):
            return self.order_by("price_per_night").all()

    # objects = PricingTierManager()
    ADULT_CHOICES = ((1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"), (6, "6"))
    tier_group = models.ForeignKey(
        "PricingTierGroup", on_delete=models.CASCADE, blank=True, null=True
    )
    number_of_adults = models.IntegerField(
        default=1, choices=ADULT_CHOICES, verbose_name=_("Number of Adults")
    )
    price_overnight = MoneyField(
        max_digits=19,
        decimal_places=2,
        verbose_name=_("Price Overnight"),
        default_currency="JPY",
    )
    price_short_term = MoneyField(
        max_digits=19,
        decimal_places=2,
        verbose_name=_("Price Short-term"),
        default_currency="JPY",
    )

    def __str__(self):
        return f"{self.price_overnight}/night, {self.price_short_term}/hour"

    def get_absolute_url(self):
        return reverse("winadmin:pricing_tier_detail", kwargs={"pk": self.pk})


class RoomTier(BaseModel):
    class Meta:
        verbose_name = _("Room Tier")
        verbose_name_plural = _("Rooms Tiers")

    name = models.CharField(max_length=255, verbose_name=_("Name"), unique=True)

    def __str__(self):
        return self.name


class Room(BaseModel):
    class RoomManager(models.Manager):
        def occupied_rooms(self):
            return super().get_queryset().filter(stay__status="checked_in")

        def rooms_and_customers(self):
            occupied_rooms = Room.objects.occupied_rooms()
            reservations = Reservation.objects.filter(stay__room__in=occupied_rooms)
            rooms_with_occupants = {}
            for room in rooms:
                customer = None
                if room in occupied_rooms:
                    if reservations.filter(stay__status="checked_in").exists():
                        customer = (
                            reservations.filter(stay__status="checked_in")
                            .first()
                            .customer
                        )
                rooms_with_occupants[room] = customer
            return rooms_with_occupants

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")

    objects = RoomManager()
    name = models.CharField(max_length=255, verbose_name=_("Name"), unique=True)
    room_tier = models.ForeignKey(
        "RoomTier",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Room Tier"),
    )

    def __str__(self):
        return f"{self.name}"


ADULT_CHOICES = ((1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"), (6, "6"))
CHILDREN_CHOICES = (
    (0, "0"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
    (5, "5"),
    (6, "6"),
)


class PricingTierGroup(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    minimum_number_of_adults = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(2)]
    )
    maximum_number_of_adults = models.IntegerField(
        validators=[MinValueValidator(4), MaxValueValidator(6)]
    )
    room_tiers = models.ManyToManyField("RoomTier")
    price_overnight_child = MoneyField(
        max_digits=19,
        decimal_places=2,
        verbose_name=_("Price Per Child Overnight"),
        default_currency="JPY",
    )
    price_short_term_child = MoneyField(
        max_digits=19,
        decimal_places=2,
        verbose_name=_("Price Per Child Short-Term"),
        default_currency="JPY",
    )
    campaign = models.ForeignKey(
        "Campaign", null=True, blank=True, on_delete=models.CASCADE
    )
    is_active = models.BooleanField(default=True)

    def create_group(self, form, formset):
        self.name = form.cleaned_data.get("name")
        self.minimum_number_of_adults = form.cleaned_data.get(
            "minimum_number_of_adults"
        )
        self.maximum_number_of_adults = form.cleaned_data.get(
            "maximum_number_of_adults"
        )
        self.price_overnight_child = form.cleaned_data.get("price_overnight_child")
        self.price_short_term_child = form.cleaned_data.get("price_short_term_child")
        room_tiers = form.cleaned_data.get("room_tiers")
        self.campaign = form.cleaned_data.get("campaigns")
        self.save()
        for tier in room_tiers:
            self.room_tiers.add(tier)

        for form in formset:
            number_of_adults = form.cleaned_data.get("number_of_adults")
            price_overnight = form.cleaned_data.get("price_overnight")
            price_short_term = form.cleaned_data.get("price_short_term")
            tier = PricingTier.objects.create(
                tier_group=self,
                number_of_adults=number_of_adults,
                price_overnight=price_overnight,
                price_short_term=price_short_term,
            )
        self.save()
        return self

    def edit_group(self, form, formset):
        self.name = form.cleaned_data.get("name")
        self.minimum_number_of_adults = form.cleaned_data.get(
            "minimum_number_of_adults"
        )
        self.maximum_number_of_adults = form.cleaned_data.get(
            "maximum_number_of_adults"
        )
        room_tiers = form.cleaned_data.get("room_tiers")
        self.campaign = form.cleaned_data.get("campaign")
        for tier in room_tiers:
            tier.save()

        for form in formset:
            form.save()

        self.save()

        return self

    def __str__(self):
        return self.name


class Stay(BaseModel):
    class StayManager(models.Manager):
        def get_stays_for_date(self, date):
            time_zone = timezone.get_default_timezone()
            target_date = (
                datetime.strptime(date, "%Y-%m-%d").astimezone(time_zone).date()
            )
            next_date = target_date + timedelta(days=1)

            # ex: Stay.objects.get_stays_for_date("2023-09-13")
            # returns all Stays that include the date within the range of their
            # start_datetime and end_datetime.
            return self.filter(
                start_datetime__date__lt=next_date, end_datetime__date__gte=target_date
            )

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
    status = StatusField()

    number_of_adults = models.IntegerField(
        choices=ADULT_CHOICES, default=1, null=True, verbose_name=_("Number of Adults")
    )
    number_of_children = models.IntegerField(
        choices=CHILDREN_CHOICES,
        default=0,
        null=True,
        verbose_name=_("Number of Children"),
    )
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    start = PendulumDateTimeField(verbose_name=_("Start"), null=True, blank=True)
    end = PendulumDateTimeField(verbose_name=_("End"), null=True, blank=True)
    # status_changed = MonitorField(monitor="status")
    price = MoneyField(
        max_digits=16, decimal_places=2, null=True, blank=True, default_currency="JPY"
    )

    def get_stay_range(self):
        return (
            self.start,
            self.end,
        )

    def status_display(self):
        return Stay.STATUS[self.status]

    def __str__(self):
        start, end = self.get_stay_range()
        return f"Stay ID: {self.id}, {_('Start')}: {start} {_('End')}: {end}"

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
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True
    )
    order_items = models.ManyToManyField(OrderItem, blank=True)

    def check_availability(self, *, start_date, end_date):
        reservations = Reservation.objects.filter(
            stay__status="reserved",
            stay__start__lte=end_date,
            stay__end__gt=start_date,
        )
        reserved_rooms_ids = reservations.values_list("stay__room__id", flat=True)
        available_rooms = self.get_possible_rooms_queryset().exclude(
            id__in=reserved_rooms_ids
        )
        return available_rooms

    def check_roomtier_availability(self, available_rooms):
        tiers = RoomTier.objects.filter(room__in=available_rooms).distinct()
        return tiers

    def get_possible_rooms_queryset(self):
        number_of_adults = self.get_number_of_adults()
        rooms_queryset = (
            Room.objects.filter(
                room_tier__pricingtiergroup__pricingtier__number_of_adults=number_of_adults
            )
            .order_by("name")
            .distinct()
        )
        return rooms_queryset

    def get_possible_roomtier_queryset(self):
        number_of_adults = self.get_number_of_adults()
        roomtier_queryset = (
            RoomTier.objects.filter(
                pricingtiergroup__pricingtier__number_of_adults=number_of_adults
            )
            .order_by("name")
            .distinct()
        )
        return roomtier_queryset

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
        if not self.check_availability(
            start_date=self.stay.start, end_date=self.stay.end
        ).exists():
            self.stay.start = selected_datetime
            self.stay.end = selected_datetime
        self.stay.save()
        return self.stay.start, self.stay.end


    def set_shortterm_date(self, selected_datetime: pendulum.DateTime):
        self.stay.start = selected_datetime
        self.stay.end = selected_datetime
        self.stay.save()
        return self.stay.start, self.stay.end

    def set_shortterm_time(self, selected_datetime: pendulum.DateTime):
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
        if not self.check_availability(
            start_date=self.stay.start, end_date=self.stay.end
        ).exists():
            self.stay.start = selected_datetime
            self.stay.end = selected_datetime
        self.stay.save()
        return self.stay.start, self.stay.end


    def reset_dates(self):
        self.stay.start = None
        self.stay.end = None
        self.stay.save()

    def reset_rooms(self):
        self.stay.room = None
        self.stay.save()

    def set_number_of_visitors(self, form):
        self.stay.number_of_adults = form.cleaned_data["number_of_adults"]
        self.stay.number_of_children = form.cleaned_data["number_of_children"]
        self.stay.save()

    def set_room(self, form, roomtier_data, start, end):
        tier = form.cleaned_data["roomtiers"]
        available_rooms = Room.objects.filter(room_tier=tier).exclude(
            stay__status__in=["reserved", "checked_in"],
            stay__start__lte=end,
            stay__end__gt=start,
        )
        self.stay.room = available_rooms.first()
        for tierprice in roomtier_data:
            if tierprice["tier"] == tier:
                self.stay.price = tierprice["price"]
        self.stay.save()
        self.save()

    def get_room_name(self):
        if self.stay.room:
            return self.stay.room.name

    def get_roomtier_name(self):
        if self.stay.room:
            return self.stay.room.room_tier.name

    def get_number_of_adults(self):
        return self.stay.number_of_adults

    def get_number_of_children(self):
        return self.stay.number_of_children

    def get_start_date(self):
        return self.stay.start

    def get_end_date(self):
        return self.stay.end

    def get_stay_period(self):
        start = self.get_start_date()
        end = self.get_end_date()
        difference = None
        if start and end:
            difference = start.diff(end)
        return difference

    def get_pricing_period(self):
        start = self.get_start_date()
        end = self.get_end_date().subtract(days=1)
        difference = None
        if start.date() == end.date():
            difference = start.diff(end)
        if start.date() < end.date():
            overnight_end = end
            difference = start.diff(overnight_end)
        return difference

    def get_stay_period_in_days(self):
        return self.get_stay_period().in_days()

    def get_stay_period_in_nights(self):
        return self.get_stay_period_in_days()

    def get_stay_period_in_hours(self):
        return self.get_stay_period().in_hours()

    def set_price(self, price):
        self.stay.price = price
        self.save()

    def get_price(self):
        return self.stay.price

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

    # def set_dates(self, selected_datetime: pendulum.DateTime):
    #     if not self.stay.start or not self.stay.end:
    #         self.stay.start = selected_datetime
    #         self.stay.end = selected_datetime
    #
    #     START_AND_END_ARE_THE_SAME = self.stay.start == self.stay.end
    #     NEW_DATE_AFTER_END = selected_datetime > self.stay.end
    #
    #     if NEW_DATE_AFTER_END and START_AND_END_ARE_THE_SAME:
    #         self.stay.end = selected_datetime
    #     else:
    #         self.stay.start = selected_datetime
    #         self.stay.end = selected_datetime
    #     self.stay.save()
    #     return self.stay.start, self.stay.end

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

    def confirm(self, customer):
        self.set_status("reserved")
        self.customer = customer
        self.save()

    def check_in(self):
        self.set_status("checked_in")

    def check_out(self):
        self.set_status("checked_out")

    def __str__(self):
        return f"Reservation id: {self.id}, Customer: {self.customer}"

    def order_items_list(self):
        items = []
        for item in self.order_items.all():
            items.append(item)
        return items

    def get_full_name(self) -> str:
        return f"{self.customer}"

    def get_absolute_url(self, pk):
        return reverse("winadmin:reservation_detail", kwargs={"pk": self.pk})


class ReservationToken(models.Model):
    class Meta:
        verbose_name = _("Reservation Token")
        verbose_name_plural = _("Reservation Tokens")

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
