from datetime import date, datetime, time, timedelta
from typing import List, Tuple
from zoneinfo import ZoneInfo

import pendulum
from dateutil.relativedelta import relativedelta

from reservations.models import Reservation
from winvillage.settings import TIME_ZONE
from django.forms import Form
from django import forms
from reservations import forms as reservation_forms

TZ = ZoneInfo(TIME_ZONE)


def check_available_options(datetime_):
    reservations_count = (
        Reservation.objects.filter(
            stay__start_date__lte=datetime_,
            stay__end_date__gte=datetime_,
            stay__status="reserved",
        )
        .select_related("stay")
        .count()
    )


def create_datetime_form(datetime_):
    form = reservation_forms.DateTimeForm(initial={"datetime": datetime_})
    return form


def compile_times_information(
    datetimes_: List[datetime],
) -> List[Tuple[datetime, Form, bool]]:
    datetimes = []
    for datetime_ in datetimes_:
        form = create_datetime_form(datetime_)
        available_options = check_available_options(datetime_)
        datetimes.append((datetime_, form, available_options))
    return datetimes


def generate_datetimes(
    date_: date = None,
    from_time: time = time(hour=9, tzinfo=TZ),
    to_time: time = time(hour=21, tzinfo=TZ),
    interval: relativedelta = relativedelta(minutes=30),
):
    """
    dts = generate_datetimes(datetime.today().date())
    for dt in dts:
        print(dt.time())

    09:00:00
    09:30:00
    10:00:00
    10:30:00
    11:00:00
    ...
    """

    if date_:
        the_date = date_
    else:
        the_date = datetime.today().date()

    from_datetime = datetime.combine(the_date, from_time)
    to_datetime = datetime.combine(the_date, to_time)

    jikan = from_datetime
    datetimes = []
    while jikan <= to_datetime:
        datetimes.append(jikan)
        jikan += interval
    return datetimes


def generate_interval(
    date_: pendulum.DateTime = None,
    from_hour: int = 9,
    to_hour: int = 21,
    time_zone: str = "UTC",
):
    """
    dts = generate_datetimes(datetime.today().date())
    for dt in dts:
        print(dt.time())

    09:00:00
    09:30:00
    10:00:00
    10:30:00
    11:00:00
    ...
    """

    if date_:
        the_date = date_
    else:
        the_date = pendulum.today(tz=time_zone)

    from_dt = the_date.at(from_hour)
    to_dt = the_date.at(to_hour)
    interval = pendulum.interval(from_dt, to_dt)

    return interval


def generate_interval_range(
    range_unit: str, range_amount: int, interval: pendulum.Interval = None
):
    if not interval:
        interval = generate_interval()
    return interval.range(unit=range_unit, amount=range_amount)
