import calendar
from datetime import datetime, date
from typing import Iterable

class TailwindCalendar(calendar.HTMLCalendar):
    cssclasses = [style + " text-3xl p-2" for style in calendar.HTMLCalendar.cssclasses]
    cssclass_month_head = "text-4xl month-head"
    cssclass_month = "text-center month"
    cssclass_year = "text-red-500 lead"


def generate_html_calendar(year, month):
    cal = TailwindCalendar()
    html_calendar = cal.formatmonth(year, month)

    return html_calendar


def get_calendar_month(the_date=datetime.now()) -> Iterable[date]:
    calendar_month = calendar.Calendar().itermonthdates(
        the_date.year, the_date.month
    )
    return calendar_month
