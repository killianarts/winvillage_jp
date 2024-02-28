import calendar
from datetime import datetime, date, timedelta
from typing import List, Iterable, Tuple
from zoneinfo import ZoneInfo

from babel.dates import format_date
from dateutil.relativedelta import relativedelta
from django import forms
from django.db.models import QuerySet
from django.utils.translation import get_language

from reservations.forms import DateForm
from reservations.forms import RoomChoiceForm
from reservations.models import Reservation, Room
from winvillage.settings import TIME_ZONE


def get_reservations(_date):
    return Reservation.objects.filter(
        stay__status="reserved",
        stay__start__lte=_date,
        stay__end__gte=_date,
    )


def get_rooms(reservations: QuerySet):
    rooms = reservations.values_list("stay__room", flat=True)


def date_check_is_available(_date):
    reservation_count = Reservation.objects.filter(
        stay__status="reserved",
        stay__start__lte=_date,
        stay__end__gte=_date,
    ).count()
    return reservation_count < 4


def room_check_is_available(room_name, _date):
    is_reserved = Reservation.objects.filter(
        stay__room__name=room_name,
        stay__status="reserved",
        stay__start__lte=_date,
        stay__end__gte=_date,
    ).exists()
    return is_reserved


def check_availability(*, queryset, _date):
    reservations = queryset.filter(
        stay__status="reserved",
        stay__start__lte=_date,
        stay__end__gte=_date,
    )
    reserved_rooms_ids = []
    if reservations.exists():
        reserved_rooms_ids = reservations.values_list("stay__room__id", flat=True)

    available_rooms = queryset.exclude(id__in=reserved_rooms_ids)

    return available_rooms


def get_form_and_rooms_data(reservation):
    date_ = reservation.get_start_date()
    number_of_adults = reservation.get_number_of_adults()
    rooms_queryset = Room.objects.filter(
        pricing_tiers__number_of_adults=number_of_adults
    ).order_by("name")

    available_rooms = check_availability(rooms_queryset, date_)

    rooms_data = []
    for room in available_rooms:
        price_per_night = room.get_price_per_night(number_of_adults)
        price_per_hour = room.get_price_per_hour(number_of_adults)
        if reservation.get_stay_period().in_days() >= 1:
            total_price = price_per_night * reservation.get_stay_period().in_days()
        else:
            total_price = price_per_hour * reservation.get_stay_period().in_hours()
        rooms_data.append(
            {
                "name": room.name,
                "price_per_night": price_per_night,
                "price_per_hour": price_per_hour,
                "total_price": total_price,
            }
        )
    if reservation.stay.room:
        initial = {"rooms": reservation.stay.room}
    else:
        initial = {}
    form = RoomChoiceForm(queryset=rooms_queryset, initial=initial)
    return form, rooms_data


def get_form_with_POST_data(reservation, request):
    number_of_adults = reservation.get_number_of_adults()
    rooms_queryset = Room.objects.filter(
        pricing_tiers__number_of_adults=number_of_adults
    ).order_by("name")
    form = RoomChoiceForm(request.POST, queryset=rooms_queryset)
    return form


def get_day_names(calendar_obj: calendar.Calendar) -> List[str]:
    """Utility function to generate day names"""
    return [calendar.day_abbr[day] for day in calendar_obj.iterweekdays()]


def get_previous_month(date_):
    previous_month_date = date_ - relativedelta(months=1)
    return previous_month_date


def get_next_month(date_):
    next_month_date = date_ + relativedelta(months=1)
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


def create_date_form(date_):
    form = DateForm(initial={"date": date_})
    return form


def compile_dates_information(
    reservation: Reservation,
    _dates: Iterable[datetime],
) -> List[Tuple[datetime, forms.Form, bool]]:
    dates = []
    number_of_adults = reservation.get_number_of_adults()
    rooms_queryset = Room.objects.filter(
        pricing_tiers__number_of_adults=number_of_adults
    ).order_by("name")
    for _date in _dates:
        form = create_date_form(_date)
        available_rooms = check_availability(queryset=rooms_queryset, _date=_date)
        is_available = True if available_rooms else False
        dates.append((_date, form, is_available))
    return dates


def before_range_start(new_range: datetime, range_start: datetime):
    return new_range < range_start


def generate_calendars(reservation: Reservation, date_: date):
    tz = ZoneInfo(TIME_ZONE)
    if date_:
        the_date = date_
    else:
        the_date = datetime.now(tz=tz).date()
    next_month_date = the_date + relativedelta(months=1)
    cal = calendar.Calendar(firstweekday=calendar.MONDAY)
    current_language = get_language()
    weekdays = get_localized_day_names(cal.firstweekday, current_language)
    the_date_dates_iter = cal.itermonthdates(the_date.year, the_date.month)
    next_month_dates_iter = cal.itermonthdates(
        next_month_date.year, next_month_date.month
    )

    calendars = {
        "weekdays": weekdays,
        "selected_month": {
            "date": the_date,
            "dates": compile_dates_information(reservation, the_date_dates_iter),
        },
        "next_month": {
            "date": next_month_date,
            "dates": compile_dates_information(reservation, next_month_dates_iter),
        },
    }
    return calendars
