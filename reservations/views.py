from datetime import date as stdlib_date
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.mail import send_mail
from django.http import HttpResponse
from django.template.response import TemplateResponse

import reservations.forms as forms
from core.utils import (
    HtmxHttpRequest,
    get_or_set_reservation_session,
    for_htmx,
    htmx_form_validate,
)
from reservations.calendar_utils import (
    get_previous_month,
    get_next_month,
    generate_calendars,
)
from reservations.forms import DateForm
from reservations.models import (
    Item,
)
from winvillage.settings import TIME_ZONE


def index(request):
    return TemplateResponse(request, "reservations/index_old.html")


@for_htmx(use_block_from_params=True)
def index(request: HtmxHttpRequest) -> HttpResponse:
    tz = ZoneInfo(TIME_ZONE)
    today_date = datetime.now(tz=tz).date()
    form = DateForm(initial={"date": today_date})
    calendars = generate_calendars(today_date)
    start_date = request.session.get("start_date", False)
    if start_date:
        start_date = stdlib_date.fromisoformat(start_date)
    end_date = request.session.get("end_date", False)
    if end_date:
        end_date = stdlib_date.fromisoformat(end_date)
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
                selected_date = calendar_cell_form.cleaned_data["date"]
                if not start_date or selected_date < start_date:
                    request.session["start_date"] = selected_date.isoformat()
                    start_date = selected_date
                    if end_date:
                        del request.session["end_date"]
                        end_date = None
                elif start_date and not end_date:
                    request.session["end_date"] = selected_date.isoformat()
                    end_date = selected_date
                elif start_date and end_date:
                    request.session["start_date"] = selected_date.isoformat()
                    start_date = selected_date
                    del request.session["end_date"]
                    end_date = None
        elif "delete_session" in request.POST:
            if start_date:
                del request.session["start_date"]
                start_date = None
            if end_date:
                del request.session["end_date"]
                end_date = None
            if "reservation_options" in request.session:
                del request.session["reservation_options"]
    context = {
        "calendars": calendars,
        "today_date": today_date,
        "form": form,
        "start_date": start_date,
        "end_date": end_date,
    }
    return TemplateResponse(request, "reservations/index.html", context)


def time_select(request: HtmxHttpRequest) -> HttpResponse:
    pass
    # return TemplateResponse(request, template_path, context)


@for_htmx(use_block_from_params=True)
def option_select(request: HtmxHttpRequest) -> HttpResponse:
    previous_url = request.META.get("HTTP_REFERER")
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
        "previous_url": previous_url,
        "grills": grills,
        "selected_grill_ids": selected_grill_ids,
    }
    return TemplateResponse(request, "reservations/index.html", context)


@htmx_form_validate(form_class=forms.ContactInfoForm)
@for_htmx(use_block_from_params=True)
def contact_information_input(request: HtmxHttpRequest) -> HttpResponse:
    initial = {
        "first_name": request.session.get("first_name", ""),
        "last_name": request.session.get("last_name", ""),
        "email": request.session.get("email", ""),
        "phone": request.session.get("phone", ""),
    }
    form = forms.ContactInfoForm(initial=initial)

    contact_info = False
    if request.method == "POST":
        form = forms.ContactInfoForm(request.POST)
        form.is_valid()
        request.session["first_name"] = form.cleaned_data["first_name"]
        request.session["last_name"] = form.cleaned_data["last_name"]
        request.session["email"] = form.cleaned_data["email"]
        request.session["phone"] = form.cleaned_data["phone"].as_national
        if form.is_valid():
            contact_info = True
    context = {"form": form, "contact_info": contact_info}
    return TemplateResponse(request, "reservations/index.html", context)


def send_confirmation_email(request):
    reservation = get_or_set_reservation_session(request)

    def format_message(name, email, message):
        return f"{name}\n{email}\n\n{message}"

    def format_subject(name, email):
        return f"[Winvillage] {name}, {email}"

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
    return HttpResponse("Sent")


# def step_4(request: HtmxHttpRequest) -> HttpResponse:
#     return _step_4(request)
#
#
# def _step_4(request: HtmxHttpRequest) -> HttpResponse:
#     reservation = get_or_set_reservation_session(request)
#     initial = {}
#     if reservation.contact_info:
#         initial = {
#             "first_name": reservation.contact_info.first_name,
#             "last_name": reservation.contact_info.last_name,
#             "email": reservation.contact_info.email,
#             "phone": reservation.contact_info.phone,
#         }
#     form = forms.Step4Form(initial=initial)
#     if request.method == "POST":
#         form = forms.Step4Form(request.POST)
#         if form.is_valid():
#             first_name = form.cleaned_data["first_name"]
#             last_name = form.cleaned_data["last_name"]
#             email = form.cleaned_data["email"]
#             phone = form.cleaned_data["phone"]
#             contact_info, created = ContactInfo.objects.get_or_create(
#                 first_name=first_name, last_name=last_name, email=email, phone=phone
#             )
#             contact_info.save()
#             reservation.contact_info = contact_info
#             reservation.save()
#             return confirm_reservation(make_get_request(request))
#
#     context = {
#         "form": form,
#     }
#     html = render_block_to_string(
#         "reservations/reservation_form.html", "step_4_form", context
#     )
#     return HttpResponse(html)
#
#
# def confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
#     return _confirm_reservation(request)
#
#
# def _confirm_reservation(request: HtmxHttpRequest) -> HttpResponse:
#     if request.method == "POST":
#         return payment_page(make_get_request(request))
#     reservation = get_or_set_reservation_session(request)
#     stay_form = forms.Step2Form(instance=reservation.stay)
#     order_items = [item for item in reservation.order_items.all()]
#     contact_info = reservation.contact_info
#     contact_info_initial = {
#         "first_name": contact_info.first_name,
#         "last_name": contact_info.last_name,
#         "email": contact_info.email,
#     }
#     contact_info_form = forms.Step4Form(initial=contact_info_initial)
#
#     context = {
#         "stay_form": stay_form,
#         "order_items": order_items,
#         "contact_info_form": contact_info_form,
#         "reservation": reservation,
#     }
#     html = render_block_to_string(
#         "reservations/reservation_form.html", "confirmation_form", context
#     )
#     return HttpResponse(html)


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
