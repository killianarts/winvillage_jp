import calendar as stdlib_calendar
import json
import locale
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event
from render_block import render_block_to_string
from django.db.models import QuerySet
from django.conf import settings
from square.client import Client
from django.core.mail import send_mail

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
    html = render_block_to_string(
        "reservations/reservation_form.html", "step_1_form", {"form": form}
    )
    return HttpResponse(html)


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
    html = render_block_to_string(
        "reservations/reservation_form.html", "step_2_form", context
    )
    return HttpResponse(html)


def step_3(request: HtmxHttpRequest) -> HttpResponse:
    return _step_3(request)


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
    reservation = get_or_set_reservation_session(request)
    initial = {}
    if reservation.contact_info:
        initial = {
            "first_name": reservation.contact_info.first_name,
            "last_name": reservation.contact_info.last_name,
            "email": reservation.contact_info.email,
        }
    form = forms.Step4Form(initial=initial)
    if request.method == "POST":
        form = forms.Step4Form(request.POST)
        if form.is_valid():
            fn = form.cleaned_data["first_name"]
            ln = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            contact_info, created = ContactInfo.objects.get_or_create(
                first_name=fn, last_name=ln, email=email
            )
            contact_info.save()
            reservation.contact_info = contact_info
            reservation.save()
            return confirm_reservation(make_get_request(request))

    context = {
        "form": form,
    }
    html = render_block_to_string(
        "reservations/reservation_form.html", "step_4_form", context
    )
    return HttpResponse(html)


def confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
    return _confirm_reservation(request)


def _confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    stay_form = forms.Step2Form(instance=reservation.stay)
    order_items = [item for item in reservation.order_items.all()]
    contact_info = reservation.contact_info
    contact_info_initial = {
        "first_name": contact_info.first_name,
        "last_name": contact_info.last_name,
        "email": contact_info.email,
    }
    contact_info_form = forms.Step4Form(initial=contact_info_initial)

    context = {
        "stay_form": stay_form,
        "order_items": order_items,
        "contact_info_form": contact_info_form,
        "reservation": reservation,
    }
    html = render_block_to_string(
        "reservations/reservation_form.html", "confirmation_form", context
    )
    return HttpResponse(html)


def payment_page(request):
    reservation = get_or_set_reservation_session(request)
    stay_form = forms.Step2Form(instance=reservation.stay)
    order_items = [item for item in reservation.order_items.all()]
    contact_info = reservation.contact_info
    contact_info_initial = {
        "first_name": contact_info.first_name,
        "last_name": contact_info.last_name,
        "email": contact_info.email,
    }
    contact_info_form = forms.Step4Form(initial=contact_info_initial)
    square_settings = settings.SQUARE_SETTINGS
    context = {
        "stay_form": stay_form,
        "order_items": order_items,
        "contact_info_form": contact_info_form,
        "reservation": reservation,
        "SQUARE_APPLICATION_ID": square_settings["SQUARE_APPLICATION_ID"],
        "SQUARE_LOCATION_ID": square_settings["SQUARE_LOCATION_ID"],
        "SQUARE_CURRENCY": square_settings["SQUARE_CURRENCY"],
    }
    return TemplateResponse(request, "reservations/payment_page.html", context)


@require_POST
def make_payment(request):
    data = json.loads(request.body)
    body = {
        "source_id": data["sourceId"],
        "idempotency_key": data["idempotencyKey"],
        "amount_money": {
            "amount": data["amountMoney"]["amount"],
            "currency": data["amountMoney"]["currency"],
        },
        "autocomplete": True,
        "location_id": data["locationId"],
        "note": "Brief description",
    }
    client = Client(
        access_token=settings.SQUARE_SETTINGS["SQUARE_ACCESS_TOKEN"],
        environment=settings.SQUARE_SETTINGS["SQUARE_ENVIRONMENT"],
    )
    payments_api = client.payments
    result = payments_api.create_payment(body=body)
    if result.is_success():
        return JsonResponse(result.body, safe=False)
    elif result.is_error():
        return JsonResponse(result.errors, safe=False)


def send_confirmation_email(request):
    reservation = get_or_set_reservation_session(request)

    def format_message(name, email, message):
        return f"{name}\n{email}\n\n{message}"

    def format_subject(name, email):
        return f"[KILLIAN.arts] {name}, {email}"

    sender_name = (
        f"{reservation.contact_info.first_name} {reservation.contact_info.last_name}"
    )
    sender_email = f"{reservation.contact_info.email}"
    message = f"Reservation Details are here! {reservation.stay.start_datetime.strftime('%Y-%M-%d')}"
    formatted_subject = format_subject(sender_name, sender_email)
    formatted_message = format_message(sender_name, sender_email, message)
    send_mail(
        formatted_subject,
        formatted_message,
        "noreply@winvillage.jp",
        [sender_email],
    )
