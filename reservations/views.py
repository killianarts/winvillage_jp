from itertools import product
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
from reservations.utils import (
    generate_weekday_names,
    get_previous_month,
    get_next_month,
    generate_calendars,
    generate_calendar,
    generate_times_for_date,
    make_pen,
)
from reservations.forms import DateForm, TimeSelectForm, TravelerForm
from reservations.models import (
    Item,
    Reservation,
    Room,
)
from reservations.tasks import send_confirmation_email
from . import utils
from .time_utils import generate_datetimes, generate_interval_range

RESERVATION_TEMPLATE = "reservations/index.html"
TIME_ZONE = "Asia/Tokyo"

@htmx_form_validate(form_class=TravelerForm)
@for_htmx(use_block_from_params=True)
def index(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    initial = {
        "number_of_adults": reservation.stay.number_of_adults,
        "number_of_children": reservation.stay.number_of_children,
    }
    form = TravelerForm(initial=initial)
    if request.method == "POST":
        form = TravelerForm(request.POST)
        if form.is_valid():
            reservation.set_number_of_visitors(form)
    context = {"form": form, "reservation": reservation}
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@for_htmx(use_block_from_params=True)
def date_select(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    today_date = pendulum.today()
    form = forms.DateTimeForm(initial={"datetime": today_date})
    calendars = generate_calendars(reservation, today_date, number_of_calendars=2)
    weekdays = generate_weekday_names()
    start = reservation.stay.start if reservation.stay.start else None
    end = reservation.stay.end if reservation.stay.end else None
    if request.method == "GET":
        if "get_previous_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_previous_month(datetime)
                form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_calendars(reservation, datetime, number_of_calendars=2)
        elif "get_next_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_next_month(datetime)
                form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_calendars(reservation, datetime, number_of_calendars=2)
    if request.method == "POST":
        if "select_date" in request.POST:
            calendar_cell_form = forms.DateTimeForm(request.POST)
            if calendar_cell_form.is_valid():
                selected_datetime = pendulum.instance(
                    calendar_cell_form.cleaned_data["datetime"]
                )
                start, end = reservation.set_dates(selected_datetime)
    context = {
        "calendars": calendars,
        "weekdays": weekdays,
        "pendulum": pendulum,
        "today_date": today_date,
        "form": form,
        "start": start,
        "end": end,
    }
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@for_htmx(use_block_from_params=True)
def room_select(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    roomtier_queryset = reservation.get_possible_roomtier_queryset()
    roomtier_data = utils.get_roomtier_data(reservation)
    form = forms.RoomTierChoiceForm(
        queryset=roomtier_queryset, initial=utils.get_form_initial_data(reservation)
    )
    if request.method == "POST":
        form = utils.get_form_with_POST_data(reservation, request)
        if form.is_valid():
            reservation.set_room(
                form,
                roomtier_data,
                reservation.get_start_date(),
                reservation.get_end_date(),
            )
    context = {"form": form, "roomtier_data": roomtier_data, "reservation": reservation}
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)

@for_htmx(use_block_from_params=True)
def time_select(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    today_dt = pendulum.today()
    form = forms.DateTimeForm(initial={"datetime": today_dt})
    time_form = TimeSelectForm()
    calendar = generate_calendar(reservation, today_dt)
    start = reservation.stay.start if reservation.stay.start else None
    end = reservation.stay.end if reservation.stay.end else None
    times = generate_times_for_date(reservation, reservation.stay.start)
    weekdays = generate_weekday_names()
    if request.method == "GET":
        if "get_previous_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_previous_month(datetime)
                form = forms.DateTimeForm(initial={"datetime": datetime})
                calendar = generate_calendar(reservation, datetime)
                times = generate_times_for_date(reservation, datetime)
        elif "get_next_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_next_month(datetime)
                form = forms.DateTimeForm(initial={"datetime": datetime})
                calendar = generate_calendar(reservation, datetime)
                times = generate_times_for_date(reservation, datetime)
    if request.method == "POST":
        if "select_date" in request.POST:
            calendar_cell_form = forms.DateTimeForm(request.POST)
            if calendar_cell_form.is_valid():
                selected_datetime = pendulum.instance(
                    calendar_cell_form.cleaned_data["datetime"]
                )
                start, end = reservation.set_shortterm_date(selected_datetime)
                times = generate_times_for_date(reservation, selected_datetime)
        if "select-time" in request.POST:
            calendar_cell_form = forms.DateTimeForm(request.POST)
            if calendar_cell_form.is_valid():
                selected_datetime = pendulum.instance(
                    calendar_cell_form.cleaned_data["datetime"]
                )
                start, end = reservation.set_shortterm_time(selected_datetime)
                times = generate_times_for_date(reservation, selected_datetime)

    context = {"form": form,
               "time_form": time_form,
               "reservation": reservation,
               "today_dt": today_dt,
               "weekdays": weekdays,
               "calendar": calendar,
               "times": times,
               "start": start,
               "end": end}
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)

@for_htmx(use_block_from_params=True)
def stay_type_select(request: HtmxHttpRequest) -> HttpResponse:
    context = {}
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)



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
    first_name = request.session["first_name"]
    last_name = request.session["last_name"]
    email = request.session["email"]
    phone = request.session["phone"]
    context = {
        "reservation": reservation,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
    }
    return TemplateResponse(request, RESERVATION_TEMPLATE, context)


@for_htmx(use_block_from_params=True)
def reservation_confirm(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    first_name = request.session["first_name"]
    last_name = request.session["last_name"]
    email = request.session["email"]
    phone = request.session["phone"]
    customer, created = Customer.objects.get_or_create(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    reservation.confirm(customer=customer)
    result = send_confirmation_email.delay(reservation.id)
    return TemplateResponse(request, RESERVATION_TEMPLATE, {"result": result})


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
