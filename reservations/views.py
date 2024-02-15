import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pendulum
from django.http import HttpResponse
from django.template.response import TemplateResponse

import reservations.forms as forms
from core.utils import (
    HtmxHttpRequest,
    get_or_set_reservation_session,
    for_htmx,
    htmx_form_validate,
)
from customer.models import Customer
from reservations.calendar_utils import (
    get_previous_month,
    get_next_month,
    generate_calendars,
)
from reservations.forms import DateForm, DateTimeForm
from reservations.models import (
    Item,
    Stay,
    Reservation,
)
from reservations.tasks import send_confirmation_email
from winvillage.settings import TIME_ZONE
from .time_utils import generate_datetimes, generate_interval_range

RESERVATION_TEMPLATE = "reservations/index.html"


@for_htmx(use_block_from_params=True)
def index(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    today_date = pendulum.today().date()
    form = DateForm(initial={"date": today_date})
    if reservation.start_time() and reservation.end_time():
        initial = {
            "start_time": reservation.start_time(),
            "end_time": reservation.end_time(),
        }
    else:
        initial = None
    time_form = forms.TimeSelectForm(initial=initial)
    calendars = generate_calendars(today_date)
    start = reservation.stay.start if reservation.stay.start else None
    end = reservation.stay.end if reservation.stay.end else None
    if request.method == "GET":
        if "get_previous_month" in request.GET:
            form = DateForm(request.GET)
            if form.is_valid():
                date = form.cleaned_data["date"]
                date = get_previous_month(date)
                form = DateForm(initial={"date": date})
                calendars = generate_calendars(date)
        elif "get_next_month" in request.GET:
            form = DateForm(request.GET)
            if form.is_valid():
                date = form.cleaned_data["date"]
                date = get_next_month(date)
                form = DateForm(initial={"date": date})
                calendars = generate_calendars(date)
    if request.method == "POST":
        if "select_date" in request.POST:
            calendar_cell_form = DateForm(request.POST)
            if calendar_cell_form.is_valid():
                selected_date = pendulum.instance(
                    calendar_cell_form.cleaned_data["date"]
                )
                start, end = reservation.set_dates(selected_date)
        if "select_time" in request.POST:
            time_form = forms.TimeSelectForm(request.POST)
            if time_form.is_valid():
                start_time = time_form.cleaned_data["start_time"]
                end_time = time_form.cleaned_data["end_time"]
                reservation.set_times(start_time, end_time)
    # price = reservation.stay.price
    context = {
        "calendars": calendars,
        "today_date": today_date,
        "form": form,
        "time_form": time_form,
        "start": start,
        "end": end,
        # "price": price,
    }
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


def times_view(request):
    datetimes = generate_interval_range(range_unit="minutes", range_amount=30)
    reservations = Reservation.objects.filter(stay__start__date="2024-1-11").filter(
        stay__end__date="2024-1-11"
    )
    return TemplateResponse(
        request,
        "reservations/times.html",
        {
            "datetimes": datetimes,
            "reservations": reservations,
        },
    )


def times_view(request):
    datetimes = generate_datetimes()
    reservations = Reservation.objects.filter(stay__start__date="2024-1-11").filter(
        stay__end__date="2024-1-11"
    )
    return TemplateResponse(
        request,
        "reservations/times.html",
        {
            "datetimes": datetimes,
            "reservations": reservations,
        },
    )


@for_htmx(use_block_from_params=True)
def option_select_with_normal_session(request: HtmxHttpRequest) -> HttpResponse:
    all_grills = (
        Item.objects.filter(category__name="grill")
        .filter(reservation_option=True)
        .order_by("pk")
    )
    grills = [
        [grill, forms.GrillOptionForm(initial={"grill_id": grill.id})]
        for grill in all_grills
    ]
    if request.method == "POST":
        form = forms.GrillOptionForm(request.POST)
        if form.is_valid():
            grill_id = form.cleaned_data["grill_id"]
            if "reservation_options" in request.session:
                if grill_id in request.session["reservation_options"]:
                    request.session["reservation_options"].remove(grill_id)
                else:
                    request.session["reservation_options"].append(grill_id)
                request.session.modified = True
            else:
                request.session["reservation_options"] = [grill_id]
    selected_grill_ids = request.session.get("reservation_options", False)
    context = {
        "grills": grills,
        "selected_grill_ids": selected_grill_ids,
    }
    return TemplateResponse(request, "reservations/index.html", context)


@for_htmx(use_block_from_params=True)
def option_select(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if request.method == "POST":
        form = forms.GrillOptionForm(request.POST)
        if form.is_valid():
            grill_id = form.cleaned_data["grill_id"]
            if "add_grill" in request.POST:
                reservation.add_order_item(grill_id)
            if "remove_grill" in request.POST:
                reservation.remove_order_item(grill_id)
    grills = reservation.get_grills()
    context = {
        "grills": grills,
    }
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@htmx_form_validate(form_class=forms.ContactInfoForm)
@for_htmx(use_block_from_params=True)
def contact_information_input(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    initial = {
        "first_name": request.session.get("first_name", ""),
        "last_name": request.session.get("last_name", ""),
        "email": request.session.get("email", ""),
        "phone": request.session.get("phone", ""),
    }
    form = forms.ContactInfoForm(initial=initial)

    contact_info = request.session.get("is_valid", False)
    if request.method == "POST":
        form = forms.ContactInfoForm(request.POST)
        if "input_form_name" in request.POST:
            print("input_form_name in POST")
        if form.is_valid():
            request.session["first_name"] = form.cleaned_data["first_name"]
            request.session["last_name"] = form.cleaned_data["last_name"]
            request.session["email"] = form.cleaned_data["email"]
            request.session["phone"] = form.cleaned_data["phone"].as_national
            reservation.first_name = form.cleaned_data["first_name"]
            reservation.last_name = form.cleaned_data["last_name"]
            reservation.email = form.cleaned_data["email"]
            reservation.phone = form.cleaned_data["phone"]
            reservation.save()
            contact_info = request.session["is_valid"] = True
        else:
            request.session["first_name"] = request.POST.get("first_name", None)
            request.session["last_name"] = request.POST.get("last_name", None)
            request.session["email"] = request.POST.get("email", None)
            request.session["phone"] = request.POST.get("phone", None)
            contact_info = request.session["is_valid"] = False
    context = {"form": form, "contact_info": contact_info}
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@for_htmx(use_block_from_params=True)
def reservation_details_review(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    context = {
        "reservation": reservation,
    }
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@for_htmx(use_block_from_params=True)
def reservation_confirm(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    response = send_confirmation_email.delay(reservation.id)
    if response:
        reservation.confirm()
        customer, created = Customer.objects.get_or_create(
            first_name=reservation.first_name,
            last_name=reservation.last_name,
            email=reservation.email,
            phone=reservation.phone,
        )
        request.session.flush()
    return TemplateResponse(request, RESERVATION_TEMPLATE, {})


# def send_confirmation_email(request):
#     reservation = get_or_set_reservation_session(request)
#
#     def format_message(name, email, message):
#         return f"{name}\n{email}\n\n{message}"
#
#     def format_subject(name, email):
#         return f"[Winvillage] {name}, {email}"
#
#     sender_name = (
#         f"{reservation.contact_info.first_name} {reservation.contact_info.last_name}"
#     )
#     sender_email = f"{reservation.contact_info.email}"
#     message = f"Reservation Details are here! {reservation.stay.start_date.strftime('%Y-%M-%d')}"
#     formatted_subject = format_subject(sender_name, sender_email)
#     formatted_message = format_message(sender_name, sender_email, message)
#     send_mail(
#         formatted_subject,
#         formatted_message,
#         "noreply@winvillage.jp",
#         [sender_email],
#     )
#     return HttpResponse("Sent")


# def payment_page(request):
#     reservation = get_or_set_reservation_session(request)
#     contact_info = reservation.contact_info
#     contact_info_initial = {
#         "first_name": contact_info.first_name,
#         "last_name": contact_info.last_name,
#         "email": contact_info.email,
#     }
#     contact_info_form = forms.Step4Form(initial=contact_info_initial)
#     square_settings = settings.SQUARE_SETTINGS
#     context = {
#         "contact_info_form": contact_info_form,
#         "reservation": reservation,
#         "SQUARE_APPLICATION_ID": square_settings["SQUARE_APPLICATION_ID"],
#         "SQUARE_LOCATION_ID": square_settings["SQUARE_LOCATION_ID"],
#         "SQUARE_CURRENCY": square_settings["SQUARE_CURRENCY"],
#     }
#     return TemplateResponse(request, "reservations/payment_page.html", context)
#
#
# @require_POST
# def make_payment(request):
#     data = json.loads(request.body)
#     body = {
#         "source_id": data["sourceId"],
#         "idempotency_key": data["idempotencyKey"],
#         "amount_money": {
#             "amount": data["amountMoney"]["amount"],
#             "currency": data["amountMoney"]["currency"],
#         },
#         "autocomplete": True,
#         "location_id": data["locationId"],
#         "note": "Brief description",
#     }
#     client = Client(
#         access_token=settings.SQUARE_SETTINGS["SQUARE_ACCESS_TOKEN"],
#         environment=settings.SQUARE_SETTINGS["SQUARE_ENVIRONMENT"],
#     )
#     payments_api = client.payments
#     result = payments_api.create_payment(body=body)
#     if result.is_success():
#         return JsonResponse(result.body, safe=False)
#     elif result.is_error():
#         return JsonResponse(result.errors, safe=False)
