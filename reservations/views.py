import calendar as stdlib_calendar
import locale
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event
from render_block import render_block_to_string
from django.db.models import QuerySet

import reservations.forms as forms
from reservations.models import (
    Stay,
    Reservation,
    ContactInfo,
    Item,
    OrderItem,
    Category,
    Order,
)
from core.utils import HtmxHttpRequest, make_get_request, get_or_set_reservation_session


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


# def test(request) -> HttpResponse:
#     current_date = datetime.now()
#     calendar_obj = stdlib_calendar.Calendar()
#     calendar_obj.setfirstweekday(stdlib_calendar.MONDAY)
#     dates_iter = calendar_obj.itermonthdates(current_date.year, current_date.month)
#     weekdays_iter = calendar_obj.iterweekdays()
#     day_names = []
#     for day in weekdays_iter:
#         day_name = stdlib_calendar.day_abbr[day]
#         day_names.append(day_name)
#
#     month_name = stdlib_calendar.month_name[current_date.month]
#
#     context = {
#         "current_date": current_date,
#         "calendar": calendar_obj,
#         "dates_iter": dates_iter,
#         "day_names": day_names,
#         "weekdays": weekdays_iter,
#         "month_name": month_name,
#     }
#     return TemplateResponse(request, "reservations/test.html", context)


def index(request):
    return TemplateResponse(request, "reservations/index.html")


# def step_1(request: HtmxHttpRequest) -> HttpResponse:
#     initial = {"stay_type": request.session.get("stay_type", None)}
#     form = forms.Step1Form(initial=initial)
#     if request.method == "POST":
#         if "submit" in request.POST:
#             form = forms.Step1Form(request.POST)
#             if form.is_valid():
#                 request.session["stay_type"] = form.cleaned_data["stay_type"]
#                 return step_2(make_get_request(request))
#     return TemplateResponse(request, "reservations/step_1.html", {"form": form})


def step_1(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    initial = {"stay_type": reservation.stay.type}
    form = forms.Step1Form(initial=initial)
    if request.method == "POST":
        if "submit" in request.POST:
            form = forms.Step1Form(request.POST)
            if form.is_valid():
                reservation.stay.type = form.cleaned_data["stay_type"]
                reservation.stay.save()
                # reservation.save()
                return step_2(make_get_request(request))
    return TemplateResponse(request, "reservations/step_1.html", {"form": form})


def step_2(request: HtmxHttpRequest) -> HttpResponse:
    return _step_2(request)


def _step_2(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    form = forms.Step2Form(instance=reservation.stay)
    if request.method == "POST":
        if "submit" in request.POST:
            form = forms.Step2Form(request.POST)
            if form.is_valid():
                reservation.stay.start_datetime = form.cleaned_data["start_datetime"]
                reservation.stay.end_datetime = form.cleaned_data["end_datetime"]
                reservation.stay.save()
                return step_3(make_get_request(request))
    current_date = datetime.now()
    calendar_obj = stdlib_calendar.Calendar()
    calendar_obj.setfirstweekday(stdlib_calendar.MONDAY)
    dates_iter = calendar_obj.itermonthdates(current_date.year, current_date.month)
    weekdays_iter = calendar_obj.iterweekdays()
    day_names = []
    for day in weekdays_iter:
        day_name = stdlib_calendar.day_abbr[day]
        day_names.append(day_name)

    month_name = stdlib_calendar.month_name[current_date.month]

    context = {
        "form": form,
        "current_date": current_date,
        "calendar": calendar_obj,
        "dates_iter": dates_iter,
        "day_names": day_names,
        "weekdays": weekdays_iter,
        "month_name": month_name,
    }
    return TemplateResponse(request, "reservations/step_2.html", context)


def step_3(request: HtmxHttpRequest) -> HttpResponse:
    return _step_3(request)


# def _step_3(request: HtmxHttpRequest) -> HttpResponse:
#     reservation = get_or_set_reservation_session(request)
#     initial = {
#         "purchase_grill": request.session.get("purchase_grill", None),
#         "purchase_food": request.session.get("purchase_food", None),
#     }
#     form = forms.Step3Form(initial=initial)
#     if request.method == "POST":
#         if "submit" in request.POST:
#             form = forms.Step3Form(request.POST)
#             if form.is_valid():
#                 request.session["purchase_grill"] = form.cleaned_data["purchase_grill"]
#                 request.session["purchase_food"] = form.cleaned_data["purchase_food"]
#                 return step_4(make_get_request(request))
#             return step_3(request)
#
#     context = {
#         "form": form,
#     }
#     return TemplateResponse(request, "reservations/step_3.html", context)


def get_combined_grill_models(request) -> QuerySet:
    reservation = get_or_set_reservation_session(request)

    all_grills = Item.objects.filter(category__title="grill")
    reserved_grills = reservation.order_items.filter(item__category__title="grill")
    reserved_grills_ids = reservation.order_items.filter(
        item__category__title="grill"
    ).values_list("id", flat=True)
    featured_reserved_grills = all_grills.filter(id__in=reserved_grills_ids)

    from django.db.models import Case, When, BooleanField

    combined_grills = (
        Grill.objects.filter(id__in=featured_grills.values_list("id", flat=True))
        .annotate(
            reserved=Case(
                When(id__in=featured_reserved_grills.values("id"), then=True),
                default=False,
                output_field=BooleanField(),
            )
        )
        .order_by("pk")
    )

    return combined_grills


@require_POST
def add_grill_reservation_option(request: HtmxHttpRequest, pk) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if reservation:
        order_item, created = OrderItem.objects.get_or_create(
            user=request.user, item_id=pk
        )
        order_item.save()
        reservation.order_items.add(order_item)
        reservation.save()
        return step_3(make_get_request(request))

    # grills = Item.objects.filter(category__title="grill", active=True)
    # context = {"grills": grills}
    # html = render_block_to_string(
    #     "reservations/reservation_form.html", "step_3_form", context
    # )
    # return HttpResponse(html)


@require_POST
def remove_grill_reservation_option(request: HtmxHttpRequest, pk):
    get_or_set_reservation_session(request)
    OrderItem.objects.filter(user=request.user, item_id=pk).first().delete()
    return step_3(make_get_request(request))


def _step_3(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if request.method == "POST":
        return step_4(make_get_request(request))
    reserved_grills_ids = reservation.order_items.filter(
        item__category__title="grill", item__active=True
    ).values_list("item_id", flat=True)
    unreserved_grills_ids = (
        Item.objects.filter(category__title="grill", active=True)
        .exclude(id__in=reserved_grills_ids)
        .values_list("id", flat=True)
    )
    all_grills_ids = list(reserved_grills_ids) + list(unreserved_grills_ids)
    all_grills = Item.objects.filter(id__in=all_grills_ids).order_by("pk")
    context = {"grills": all_grills, "reserved_grill_ids": reserved_grills_ids}
    html = render_block_to_string(
        "reservations/reservation_form.html", "step_3_form", context
    )
    return HttpResponse(html)


def step_4(request: HtmxHttpRequest) -> HttpResponse:
    return _step_4(request)


def _step_4(request: HtmxHttpRequest) -> HttpResponse:
    initial = {
        "first_name": request.session.get("first_name", None),
        "last_name": request.session.get("last_name", None),
        "email": request.session.get("email", None),
    }
    form = forms.Step4Form(initial=initial)
    if request.method == "POST":
        form = forms.Step4Form(request.POST)
        if form.is_valid():
            request.session["first_name"] = form.cleaned_data["first_name"]
            request.session["last_name"] = form.cleaned_data["last_name"]
            request.session["email"] = form.cleaned_data["email"]
            return confirm_reservation(make_get_request(request))

    context = {
        "form": form,
    }
    return TemplateResponse(request, "reservations/step_4.html", context)


def confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
    return _confirm_reservation(request)


def _confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
    initial = {
        "stay_type": request.session.get("stay_type", None),
        "stay_date_start": datetime.fromisoformat(
            request.session.get("stay_date_start", None)
        ),
        "stay_date_end": datetime.fromisoformat(
            request.session.get("stay_date_end", None)
        ),
        "purchase_grill": request.session.get("purchase_grill", None),
        "purchase_food": request.session.get("purchase_food", None),
        "first_name": request.session.get("first_name", None),
        "last_name": request.session.get("last_name", None),
        "email": request.session.get("email", None),
    }
    form = forms.ConfirmationForm(initial=initial)
    context = {"form": form}
    if request.method == "POST":
        form = forms.ConfirmationForm(request.POST)
        if form.is_valid():
            stay_type = initial["stay_type"]
            stay_date_start = form.cleaned_data["stay_date_start"]
            stay_date_end = form.cleaned_data["stay_date_end"]
            purchase_grill = form.cleaned_data["purchase_grill"]
            purchase_food = form.cleaned_data["purchase_food"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]

            stay_obj = Stay.objects.create(stay_type, stay_date_start, stay_date_end)
            stay_obj.save()

            contact_info = ContactInfo.objects.get_or_create(
                first_name, last_name, email
            )

            reservation = Reservation.objects.get_or_create(stay_obj, contact_info)
            reservation.save()
            reservation_options = []
            if purchase_grill:
                grill = Grill.objects.get_or_create(pk=1)
                option, created = ReservationOption.objects.get_or_create(
                    content_type=grill
                )
                if created:
                    option.save()
                reservation_options.append(option)
            if purchase_food:
                food = Food.objects.get_or_create(pk=1)
                option, created = ReservationOption.objects.get_or_create(
                    content_type=food
                )
                if created:
                    option.save()
                reservation_options.append(option)
            for option in reservation_options:
                reservation.reservation_options.add(option)

            return TemplateResponse(
                request,
                "reservations/reservation_completed.html",
            )
    return TemplateResponse(request, "reservations/confirmation_step.html", context)
