from django.template.response import TemplateResponse
from django.shortcuts import render
from django.http import HttpResponse
# from .calendar_utils import generate_html_calendar
from datetime import datetime
from django.utils.html import format_html, mark_safe
import winvillage.settings as settings

import calendar
import locale
from django.utils import translation


# class TailwindCalendar(calendar.HTMLCalendar):
#     cssclasses = [style + " text-3xl p-2" for style in calendar.HTMLCalendar.cssclasses]
#     cssclass_month_head = "text-4xl month-head"
#     cssclass_month = "text-center month"
#     cssclass_year = "text-red-500 lead"
#
#
# def generate_html_calendar_month(year, month):
#     cal = TailwindCalendar()
#     html_calendar_month = cal.formatmonth(year, month)
#
#     return html_calendar_month

# def index(request) -> HttpResponse:
#     current_date = datetime.now()
#     current_year = current_date.year
#     current_month = current_date.month
#     calendar_html = generate_html_calendar(current_year, current_month)
#     formatted_calendar = format_html(calendar_html, mark_safe(calendar_html))
#     return TemplateResponse(request, 'reservations/index.html', {'calendar': formatted_calendar})

def set_locale(locale_code):
    # Save the current locale
    current_locale = locale.setlocale(locale.LC_ALL)

    try:
        new_locale = locale.setlocale(locale.LC_ALL, f"{locale_code}.UTF-8")
    except locale.Error:
        try:
            new_locale = locale.setlocale(locale.LC_ALL, locale_code)
        except locale.Error:
            raise RuntimeError("Locale not available on this system.")

    return current_locale, new_locale


def index(request) -> HttpResponse:
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    calendar_obj = calendar.Calendar()
    calendar_obj.setfirstweekday(calendar.MONDAY)
    dates_iter = calendar_obj.itermonthdates(current_year, current_month)
    weekdays_iter = calendar_obj.iterweekdays()
    code_parts = request.LANGUAGE_CODE.split('-')
    LOCALE = '_'.join(code_parts)
    # current_locale, new_locale = set_locale(LOCALE)
    day_names = []
    for day in weekdays_iter:
        day_name = calendar.day_abbr[day]
        day_names.append(day_name)

    month_name = calendar.month_name[current_month]

    context = {'current_date': current_date,
               'dates_iter': dates_iter,
               'day_names': day_names,
               'month_name': month_name, }
    # dates_iter = generate_full_calendar(current_year, current_month)
    return TemplateResponse(request, 'reservations/index.html', context)
