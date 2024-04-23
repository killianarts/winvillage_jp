import calendar
from datetime import datetime, date, timedelta
from typing import List, Iterable

import pendulum
from babel.dates import format_date
from django.utils.translation import get_language

from reservations.forms import DateTimeForm, RoomTierChoiceForm
from reservations.models import Reservation, Stay, Room, RoomTier


def make_pen(dt: datetime | date) -> pendulum.DateTime:
    return pendulum.local(dt.year, dt.month, dt.day)


# def make_pens(dates: Iterable[date]) -> Generator[pendulum.DateTime]:
#     for date_ in dates:
#         yield pendulum.local(date_.year, date_.month, date_.day)


def make_pens(dates: Iterable[date]) -> List[pendulum.DateTime]:
    pens = []
    for date_ in dates:
        pens.append(make_pen(date_))
    return pens


def campaign_occurrences(reservation, campaign):
    return campaign.recurrences.between(
        reservation.get_start_date(),
        reservation.get_end_date(),
        dtstart=reservation.get_start_date(),
        dtend=reservation.get_end_date(),
        inc=True,
    )


def get_room_price(reservation: Reservation, room: Room):
    period = reservation.get_stay_period()
    number_of_adults = reservation.get_number_of_adults()

    def get_overnight_price(group):
        return group.pricingtier_set.filter(number_of_adults=number_of_adults).values_list("price_overnight", flat=True)

    def get_short_term_price(group):
        return group.pricingtier_set.filter(number_of_adults=number_of_adults).values_list(
            "price_short_term", flat=True
        )

    # There may be multiple pricingtiergroup's that contain a compaign that is applicable to a room on a given date.
    # To resolve the conflict, I'm choosing to get the most recently defined group.
    # This feels like a very important choice being done with one line of code.
    # TODO: Consider ways of formalizing this choice more thoughtfully and visibly.
    pricingtiergroups = room.room_tier.pricingtiergroup_set.all().order_by("updated_at")
    dates_with_prices = {}
    for group in pricingtiergroups:
        for period_datetime in period.range("days"):
            if group.campaign:
                for campaign_date in campaign_occurrences(reservation, group.campaign):
                    if period_datetime.date() == campaign_date.date():
                        if period.in_days() >= 1:
                            dates_with_prices[period_datetime.date()] = get_overnight_price(group)

                        else:
                            dates_with_prices[period_datetime.date()] = get_short_term_price(group)

            elif not group.campaign:
                if period.in_days() >= 1:
                    dates_with_prices[period_datetime.date()] = get_overnight_price(group)
                else:
                    dates_with_prices[period_datetime.date()] = get_short_term_price(group)

    price = 0
    for date_, price_ in dates_with_prices.items():
        price += price_.first()
    return price


# def get_form_and_rooms_data(reservation):
#     start = reservation.get_start_date()
#     end = reservation.get_end_date()
#     rooms_queryset = reservation.get_possible_rooms_queryset()
#     available_rooms = reservation.check_availability(start_date=start, end_date=end)
#     rooms_data = []
#     if available_rooms:
#         for room in available_rooms:
#             # Check if the period between the start and end dates falls into an active campaign.
#             # First we need to know which PricingTierGroups this room is in.
#             # We get that information through its RoomTier
#             price = get_room_price(reservation=reservation, room=room)
#             rooms_data.append(
#                 {
#                     "room": room,
#                     "price": price,
#                 }
#             )
#     room_name = reservation.get_room_name()
#     initial = {}
#     if room_name:
#         if reservation.get_possible_rooms_queryset().filter(name=room_name).exists():
#             initial = {"rooms": reservation.stay.room}
#         else:
#             reservation.reset_rooms()
#     form = RoomChoiceForm(queryset=rooms_queryset, initial=initial)
#     return form, rooms_data


# TODO: Move utilities to the Reservation model.
def get_roomtier_price(reservation: Reservation, roomtier: RoomTier, number_of_adults: int):
    def get_overnight_price(group):
        return (
            group.pricingtier_set.filter(number_of_adults=number_of_adults)
            .values_list("price_overnight", flat=True)
            .first()
        )

    def get_short_term_price(group):
        return (
            group.pricingtier_set.filter(number_of_adults=number_of_adults)
            .values_list("price_short_term", flat=True)
            .first()
        )

    def get_child_overnight_price(group):
        return group.price_overnight_child

    def get_child_short_term_price(group):
        return group.price_short_term_child

    # There may be multiple pricingtiergroup's that contain a compaign that is applicable to a room on a given date.
    # To resolve the conflict, I'm choosing to get the most recently defined group.
    # This feels like a very important choice being done with one line of code.
    # TODO: Consider ways of formalizing this choice more thoughtfully and visibly.
    pricingtiergroups = roomtier.pricingtiergroup_set.all().order_by("updated_at")
    dates_with_prices = {}
    period = reservation.get_stay_period()
    number_of_nights = period.in_days()
    pricing_period = reservation.get_pricing_period()
    for group in pricingtiergroups:
        for period_datetime in pricing_period:
            if group.campaign:
                for campaign_date in campaign_occurrences(reservation, group.campaign):
                    if period_datetime.date() == campaign_date.date():
                        if number_of_nights >= 1:
                            dates_with_prices[period_datetime.date()] = {
                                "price_adult": get_overnight_price(group),
                                "price_child": get_child_overnight_price(group),
                            }
                        else:
                            dates_with_prices[period_datetime.date()] = {
                                "price_adult": get_short_term_price(group),
                                "price_child": get_child_short_term_price(group),
                            }

            elif not group.campaign:
                if number_of_nights >= 1:
                    dates_with_prices[period_datetime.date()] = {
                        "price_adult": get_overnight_price(group),
                        "price_child": get_child_overnight_price(group),
                    }
                else:
                    dates_with_prices[period_datetime.date()] = {
                        "price_adult": get_short_term_price(group),
                        "price_child": get_child_short_term_price(group),
                    }

    price = 0
    for date_, prices_ in dates_with_prices.items():
        price += prices_["price_adult"]
    for date_, prices_ in dates_with_prices.items():
        price += prices_["price_child"] * reservation.get_number_of_children()
    return price


def get_form_and_roomtier_data(reservation):
    start = reservation.get_start_date()
    end = reservation.get_end_date()
    number_of_adults = reservation.get_number_of_adults()
    roomtier_queryset = reservation.get_possible_roomtier_queryset()
    available_rooms = reservation.check_availability(start_date=start, end_date=end)
    available_roomtiers = reservation.check_roomtier_availability(available_rooms)
    roomtier_data = []
    if available_roomtiers:
        for tier in available_roomtiers:
            # Check if the period between the start and end dates falls into an active campaign.
            # First we need to know which PricingTierGroups this room is in.
            # We get that information through its RoomTier
            price = get_roomtier_price(reservation=reservation, roomtier=tier, number_of_adults=number_of_adults)
            roomtier_data.append(
                {
                    "tier": tier,
                    "price": price,
                }
            )
    roomtier_name = reservation.get_roomtier_name()
    initial = {}
    if roomtier_name:
        if reservation.get_possible_roomtier_queryset().filter(name=roomtier_name).exists():
            initial = {"roomtiers": reservation.stay.room.room_tier}
        else:
            reservation.reset_rooms()
    form = RoomTierChoiceForm(queryset=roomtier_queryset, initial=initial)
    return form, roomtier_data


# def get_form_and_rooms_data(reservation):
#     rooms_queryset = reservation.get_possible_rooms_queryset()
#     room = Room.objects.get(id=1)
#     number_of_adults = 3
#     rooms_data = []
#     price = get_room_price(
#         reservation=reservation, room=room, number_of_adults=number_of_adults
#     )
#     rooms_data.append(
#         {
#             "name": room.name,
#             "price": price,
#         }
#     )
#     room_name = reservation.get_room_name()
#     initial = {}
#     if room_name:
#         if reservation.get_possible_rooms_queryset().filter(name=room_name).exists():
#             initial = {"rooms": reservation.stay.room}
#         else:
#             reservation.reset_rooms()
#     form = RoomChoiceForm(queryset=rooms_queryset, initial=initial)
#     return form, rooms_data


def get_form_with_POST_data(reservation, request):
    roomtier_queryset = reservation.get_possible_roomtier_queryset()
    form = RoomTierChoiceForm(request.POST, queryset=roomtier_queryset)
    return form


def get_previous_month(date_):
    previous_month_date = date_.subtract(months=1)
    return previous_month_date


def get_next_month(date_):
    next_month_date = date_.add(months=1)
    return next_month_date


def get_localized_month_name(date_: date, locale="en"):
    return format_date(date_, "MMMM", locale=locale)


def get_localized_day_names(firstweekday, locale="en"):
    # Create a date object for the first day of current week
    now = date.today()
    start = now - timedelta(days=now.weekday()) + timedelta(days=firstweekday)

    # Generate dates for a week starting from `start`
    week_dates = [start + timedelta(days=i) for i in range(7)]

    # Now return the localized weekday names
    return [format_date(d, "EEE", locale=locale) for d in week_dates]


# def compile_dates_information(
#     reservation: Reservation,
#     _dates: Iterable[datetime],
# ) -> List[Tuple[datetime, forms.Form, QuerySet]]:
#     dates = []
#     number_of_adults = reservation.get_number_of_adults()
#     rooms_queryset = Room.objects.filter(
#         pricing_tiers__number_of_adults=number_of_adults
#     ).order_by("name")
#     for _date in _dates:
#         form = DateForm(initial={"date": _date})
#         available_rooms = check_availability(
#             number_of_adults=number_of_adults, queryset=rooms_queryset, _date=_date
#         )
#         # TODO: Figure out how to speed this up.
#         #  The calls to `available_rooms` are causing about 74 queries.
#         is_available = True if available_rooms else False
#         if (
#             not is_available
#             and reservation.get_start_date() == _date
#             or reservation.get_end_date() == _date
#         ):
#             reservation.reset_dates()
#         dates.append((_date, form, is_available))
#     return dates


def compile_dates_information(reservation: Reservation, datetimes_iter):
    rooms_reserved = []
    for dt in datetimes_iter:
        rooms_reserved.append({"datetime": dt, "room_ids": set()})

    possible_rooms = reservation.get_possible_rooms_queryset()
    possible_rooms_ids = {room_id for room_id in possible_rooms.values_list("id", flat=True)}
    stays_query = Stay.objects.filter(
        room__in=possible_rooms,
        start__lte=max(datetimes_iter),
        end__gte=min(datetimes_iter),
    ).values("room_id", "start", "end")

    for stay in stays_query:
        stay_room_id = stay["room_id"]
        start = stay["start"]
        end = stay["end"]
        for room in rooms_reserved:
            #                            v < instead of <=
            if start <= room["datetime"] < end:
                room["room_ids"].add(stay_room_id)
    dates_and_forms = []
    start_date = reservation.get_start_date() if reservation.get_start_date() else None
    end_date = reservation.get_end_date() if reservation.get_end_date() else None
    for room in rooms_reserved:
        room_is_available = not possible_rooms_ids.issubset(room["room_ids"])
        if start_date or end_date:
            if not room_is_available and start_date <= room["datetime"] <= end_date:
                reservation.reset_dates()
        form = DateTimeForm(initial={"datetime": room["datetime"]}) if room_is_available else None
        dates_and_forms.append([room["datetime"], form])
    return dates_and_forms


# We avoid serializing standard datetime objects into Pendulum DateTimes by initializing them correctly here.
class PendulumCalendar(calendar.Calendar):
    def itermonthpens(self, year, month, default_hour=10):
        pens = []
        for y, m, d in self.itermonthdays3(year, month):
            pens.append(pendulum.datetime(year=y, month=m, day=d, hour=default_hour))
        return pens

    def itermonthnaivepens(self, year, month, default_hour=10):
        pens = []
        for y, m, d in self.itermonthdays3(year, month):
            pens.append(pendulum.naive(year=y, month=m, day=d, hour=default_hour))
        return pens


def generate_calendars(reservation: Reservation, date_: pendulum.Date = None):
    if not date_:
        date_ = pendulum.now()
    next_month_date = date_.add(months=1)
    cal = PendulumCalendar(firstweekday=calendar.MONDAY)
    selected_dates = cal.itermonthnaivepens(date_.year, date_.month)
    next_month_dates = cal.itermonthnaivepens(next_month_date.year, next_month_date.month)

    selected_dates_and_forms = compile_dates_information(reservation, selected_dates)
    next_month_dates_and_forms = compile_dates_information(reservation, next_month_dates)
    current_language = get_language()
    weekdays = get_localized_day_names(cal.firstweekday, current_language)
    calendars = {
        "weekdays": weekdays,
        "selected_month": {"date": date_, "datetimes": selected_dates_and_forms},
        "next_month": {
            "date": next_month_date,
            "datetimes": next_month_dates_and_forms,
        },
    }
    return calendars


def generate_campaign_calendars(
    campaign=None,
    date_: pendulum.Date = None,
):
    if not date_:
        date_ = pendulum.now()
    current = date_
    next = date_.add(months=1)

    def get_nstart_and_nend(pen):
        start = pen.start_of("month")
        nstart = pendulum.naive(start.year, start.month, start.day)
        end = pen.end_of("month")
        nend = pendulum.naive(end.year, end.month, end.day)
        return nstart, nend

    current_nstart, current_nend = get_nstart_and_nend(current)
    next_nstart, next_nend = get_nstart_and_nend(next)

    def get_occurrences(start, end, dates):
        occurrences = {}
        if campaign:
            campaign_occurrences = campaign.recurrences.between(
                after=start,
                before=end,
                dtstart=start,
                inc=True,
            )
            for dt in dates:
                occurrences[dt] = dt in campaign_occurrences
        else:
            for dt in dates:
                occurrences[dt] = False
        return occurrences

    next_month_date = date_.add(months=1)
    cal = PendulumCalendar(firstweekday=calendar.MONDAY)
    selected_month_dates = cal.itermonthnaivepens(date_.year, date_.month, default_hour=0)
    next_month_dates = cal.itermonthnaivepens(next_month_date.year, next_month_date.month, default_hour=0)
    selected_month_occurrences = get_occurrences(start=current_nstart, end=current_nend, dates=selected_month_dates)
    next_month_occurrences = get_occurrences(start=next_nstart, end=next_nend, dates=next_month_dates)
    current_language = get_language()
    weekdays = get_localized_day_names(cal.firstweekday, current_language)
    calendars = {
        "weekdays": weekdays,
        "selected_month": {"date": date_, "occurrences": selected_month_occurrences},
        "next_month": {
            "date": next_month_date,
            "occurrences": next_month_occurrences,
        },
    }
    return calendars
