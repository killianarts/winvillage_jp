from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.utils.dates import WEEKDAYS, MONTHS

from reservations.calendar_utils import get_calendar_month
from datetime import datetime
import calendar as stdlib_calendar

import locale
from django.utils import translation
import reservations.forms as forms
from reservations.models import Room


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


def test(request) -> HttpResponse:
    current_date = datetime.now()
    calendar_obj = stdlib_calendar.Calendar()
    calendar_obj.setfirstweekday(stdlib_calendar.MONDAY)
    dates_iter = calendar_obj.itermonthdates(current_date.year, current_date.month)
    weekdays_iter = calendar_obj.iterweekdays()
    # code_parts = request.LANGUAGE_CODE.split("-")
    # LOCALE = "_".join(code_parts)
    # current_locale, new_locale = set_locale(LOCALE)
    day_names = []
    for day in weekdays_iter:
        day_name = stdlib_calendar.day_abbr[day]
        day_names.append(day_name)

    month_name = stdlib_calendar.month_name[current_date.month]

    context = {
        "current_date": current_date,
        "calendar": calendar_obj,
        "dates_iter": dates_iter,
        "day_names": day_names,
        "weekdays": weekdays_iter,
        "month_name": month_name,
    }
    # dates_iter = generate_full_calendar(current_year, current_month)
    return TemplateResponse(request, "reservations/test.html", context)


def index(request):
    return TemplateResponse(request, "reservations/index.html")


def step_1(request):
    initial = {"stay_type": request.session.get("stay_type", None)}
    form = forms.Step1Form(initial=initial)
    return TemplateResponse(request, "reservations/step_1.html", {"form": form})


@require_POST
def step_2(request):
    step_1_form = forms.Step1Form(request.POST)
    if step_1_form.is_valid():
        request.session["stay_type"] = step_1_form.cleaned_data["stay_type"]
    initial = {"stay_length": request.session.get("stay_length", None)}
    form = forms.Step2Form(initial=initial)
    the_date = datetime.now()
    calendar_month = get_calendar_month(the_date)
    calendar = stdlib_calendar.Calendar()
    return TemplateResponse(
        request,
        "reservations/step_2.html",
        {
            "form": form,
            "calendar_month": calendar_month,
            "the_date": the_date,
            "calendar": calendar,
        },
    )
