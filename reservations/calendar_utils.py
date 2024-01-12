import calendar
from datetime import datetime, date, timedelta, time
from typing import List, Iterable, Tuple
from zoneinfo import ZoneInfo

from babel.dates import format_date
from dateutil.relativedelta import relativedelta
from django import forms
from django.utils import timezone
from django.utils.translation import get_language

from reservations.forms import DateForm
from reservations.models import Reservation
from winvillage.settings import TIME_ZONE


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


def check_availability(date_):
    # attach timezone information to date object
    tzinfo = timezone.get_current_timezone()
    datetime_with_tz = timezone.make_aware(datetime.combine(date_, time.min), tzinfo)

    reservations_count = (
        Reservation.objects.filter(
            stay__start__date__lte=datetime_with_tz,
            stay__end__date__gte=datetime_with_tz,
            stay__status="reserved",
        )
        .select_related("stay")
        .count()
    )
    return reservations_count < 4


def create_date_form(date_):
    form = DateForm(initial={"date": date_})
    return form


def compile_dates_information(
    dates_: Iterable[datetime],
) -> List[Tuple[datetime, forms.Form, bool]]:
    dates = []
    for date_ in dates_:
        form = create_date_form(date_)
        is_available = check_availability(date_)
        dates.append((date_, form, is_available))
    return dates


def before_range_start(new_range: datetime, range_start: datetime):
    return new_range < range_start


def generate_calendars(date_: date):
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
            "dates": compile_dates_information(the_date_dates_iter),
        },
        "next_month": {
            "date": next_month_date,
            "dates": compile_dates_information(next_month_dates_iter),
        },
    }
    return calendars
