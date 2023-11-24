import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import activate, deactivate
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event, HttpResponseClientRedirect
from sendgrid import Mail, SendGridAPIClient
from square.client import Client

from core.models import Item, Category, Transaction, Customer
from core.utils import (
    HtmxHttpRequest,
    make_get_request,
    get_or_set_reservation_session,
    for_htmx,
    htmx_form_validate,
)
from reservations import forms
from reservations.calendar_utils import (
    generate_calendars,
    get_previous_month,
    get_next_month,
)
from reservations.forms import DateForm
from reservations.models import Reservation, Stay
from reservations.tasks import send_confirmation_email
from winadmin.forms import (
    LoginForm,
    ItemCreateForm,
    CategoryCreateForm,
    ItemEditForm,
    CategoryDetailForm,
    TransactionCreateForm,
    SetLedgerPeriodForm,
    SetReservationPeriodForm,
    ReservationCreateForm,
    ReservationDetailForm,
    SquarePaymentTokenForm,
)
from winvillage import settings
from winvillage.settings import TIME_ZONE

SQUARE_APPLICATION_ID = settings.SQUARE_SETTINGS["SQUARE_APPLICATION_ID"]
SQUARE_LOCATION_ID = settings.SQUARE_SETTINGS["SQUARE_LOCATION_ID"]
SQUARE_CURRENCY = settings.SQUARE_SETTINGS["SQUARE_CURRENCY"]
SQUARE_ACCESS_TOKEN = settings.SQUARE_SETTINGS["SQUARE_ACCESS_TOKEN"]
SQUARE_ENVIRONMENT = settings.SQUARE_SETTINGS["SQUARE_ENVIRONMENT"]

TIMEZONE = "Asia/Tokyo"


# Index and Login
@login_required(login_url="winadmin:login_page")
def index(request: HtmxHttpRequest) -> HttpResponse:
    greeting = "Hello"
    return TemplateResponse(request, "winadmin/index.html", {"greeting": greeting})


def inventory_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from inventory."}
    )


def sale_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from sales."}
    )


@htmx_form_validate(form_class=LoginForm)
def login_page(request: HtmxHttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("winadmin:index")
    form = LoginForm()

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("winadmin:index")
            else:
                messages.error(request=request, message="Huh?")
    context = {"form": form}
    return TemplateResponse(request, "winadmin/login_page.html", context)


@login_required(login_url="winadmin:login_page")
def _logout(request: HtmxHttpRequest) -> HttpResponse:
    logout(request)
    return redirect("winadmin:login_page")


# Inventory


@login_required(login_url="winadmin:login_page")
def item_list(request: HtmxHttpRequest) -> HttpResponse:
    items = Item.objects.all()
    context = {"items": items}
    return TemplateResponse(request, "winadmin/inventory/item_list.html", context)


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def item_create(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        if "submit" in request.POST:
            form = ItemCreateForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, _("Item Successfully Added"))
    form = ItemCreateForm()
    return trigger_client_event(
        TemplateResponse(
            request, "winadmin/inventory/item_create.html", {"form": form}
        ),
        "getMessages",
    )


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def category_create(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CategoryCreateForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            category = Category.objects.create(name=name)
            category.save()
            messages.success(request, _("Category Successfully Added"))
            return HttpResponseClientRedirect(reverse("winadmin:category_list"))
        else:
            messages.error(request, _("Input category title"))
    form = CategoryCreateForm()
    context = {"form": form}
    return trigger_client_event(
        TemplateResponse(request, "winadmin/inventory/category_create.html", context),
        "getMessages",
    )


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def category_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    if request.method == "POST":
        form = CategoryCreateForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            category = get_object_or_404(Category, pk=pk)
            category.name = name
            category.save()
            messages.success(request, _("Category Successfully Edited"))
        else:
            messages.error(request, _("Input category name"))
    category = get_object_or_404(Category, pk=pk)
    form = CategoryDetailForm(initial={"name": category.name})
    context = {"form": form, "category": category}
    return trigger_client_event(
        TemplateResponse(request, "winadmin/inventory/category_detail.html", context),
        "getMessage",
    )


def category_list(request: HtmxHttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    context = {
        "categories": categories,
    }
    return TemplateResponse(request, "winadmin/inventory/category_list.html", context)


@login_required(login_url="winadmin:login_page")
@htmx_form_validate(form_class=ItemEditForm)
@for_htmx(use_block_from_params=True)
def item_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    form = ItemEditForm(instance=item)
    if request.method == "POST":
        form = ItemEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, _("Item Successfully Edited"))
        else:
            form = ItemEditForm(request.POST, instance=item)
            messages.error(request, _("Error"))
    return trigger_client_event(
        TemplateResponse(
            request, "winadmin/inventory/item_detail.html", {"form": form, "item": item}
        ),
        "getMessages",
    )


@require_POST
@login_required(login_url="winadmin:login_page")
def item_delete(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    form = ItemEditForm(request.POST, instance=item)
    if form.is_valid():
        item.delete()
        messages.success(request, _("Item Successfully Deleted"))
    else:
        form = ItemEditForm(request.POST, instance=item)
        messages.error(request, _("Error"))
    return redirect("winadmin:list_inventory")


# Transactions


@login_required(login_url="winadmin:login_page")
def sale_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    return _sales_list_by_period(request)


def get_current_year_and_month(request, tz=TIMEZONE):
    active_timezone = activate(tz)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    return year, month


def get_balance_and_ledger(sales: Transaction):
    balance = 0
    ledger = []
    for sale in sales:
        if sale.name == "sale":
            balance += sale.total_price_rounded
        elif sale.name == "return":
            balance -= sale.total_price_rounded
        ledger.append([sale, balance])
    return balance, ledger


@for_htmx(use_block_from_params=True)
def _sales_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    sales = Transaction.sales.all()
    year, month = get_current_year_and_month(request)
    deactivate()
    if request.htmx:
        form = SetLedgerPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    else:
        form = SetLedgerPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    sales = sales.filter(transaction_datetime__year=year).filter(
        transaction_datetime__month=month
    )
    balance, ledger = get_balance_and_ledger(sales)
    context = {
        "ledger": ledger,
        "final_balance": balance,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/transactions/sales_list_by_period.html", context
    )


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def transaction_create(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Transaction Created Successfully"))
        elif not form.is_valid():
            messages.error(request, _("Transaction Couldn't Be Created"))
    form = TransactionCreateForm()
    context = {"form": form}
    return trigger_client_event(
        TemplateResponse(
            request, "winadmin/transactions/transaction_create.html", context
        ),
        "getMessages",
    )


@for_htmx(use_block_from_params=True)
@login_required(login_url="winadmin:login_page")
def transaction_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    transactions = Transaction.objects.all()
    year, month = get_current_year_and_month(request)
    deactivate()
    if request.htmx:
        form = SetLedgerPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    else:
        form = SetLedgerPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    transactions = transactions.filter(transaction_datetime__year=year).filter(
        transaction_datetime__month=month
    )
    balance, ledger = get_balance_and_ledger(transactions)
    context = {
        "ledger": ledger,
        "final_balance": balance,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/transactions/transaction_list_by_period.html", context
    )


@login_required(login_url="winadmin:login_page")
def transaction_detail(request: HtmxHttpRequest) -> HttpResponse:
    return _transaction_detail(request)


def _transaction_detail(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.INFO, _("Transaction Created Successfully")
            )
            return _transaction_create(make_get_request(request))
        elif not form.is_valid():
            return TemplateResponse(
                request, "winadmin/transactions/transaction_create.html", {}
            )
    form = TransactionCreateForm()
    context = {"form": form}
    return TemplateResponse(
        request, "winadmin/transactions/transaction_create.html", context
    )


# Reservations


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def reservation_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    reservations = (
        Reservation.objects.select_related("stay")
        .exclude(stay__status="not_reserved")
        .order_by("stay__start_date")
    )
    form = []
    active_timezone = activate(TIMEZONE)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    deactivate()
    if request.htmx:
        form = SetReservationPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    else:
        form = SetReservationPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    reservations = reservations.filter(stay__start_date__year=year).filter(
        stay__start_date__month=month
    )
    context = {
        "reservations": reservations,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/reservations/reservation_list_by_period.html", context
    )


@htmx_form_validate(form_class=ReservationCreateForm)
@for_htmx(use_block_from_params=True)
def reservation_create_no_calendar(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    initial = {}
    if reservation is not None:
        initial["first_name"] = reservation.first_name
        initial["last_name"] = reservation.last_name
        initial["email"] = reservation.email
    if reservation.stay is not None:
        initial["stay_type"] = reservation.stay.stay_type
        initial["start_date"] = reservation.stay.start_date
        initial["end_date"] = reservation.stay.end_date
    grills = reservation.get_grills()
    if request.method == "POST":
        form = ReservationCreateForm(request.POST)
        if form.is_valid():
            stay_type = form.cleaned_data["stay_type"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            if not reservation.stay:
                stay = Stay.objects.create(
                    stay_type=stay_type,
                    start_date=start_date,
                    end_date=end_date,
                )
                reservation.stay = stay
                reservation.save()
            else:
                reservation.stay.stay_type = stay_type
                reservation.stay.start_date = start_date
                reservation.stay.end_date = end_date
                reservation.stay.save()
                reservation.save()
    form = ReservationCreateForm(initial=initial)
    context = {
        "form": form,
        "reservation": reservation,
        "grill": grills,
    }
    return TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )


RESERVATION_TEMPLATE = "winadmin/reservations/reservation_create.html"


@for_htmx(use_block_from_params=True)
def datetime_select(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    tz = ZoneInfo(TIME_ZONE)
    today_date = datetime.now(tz=tz).date()
    form = DateForm(initial={"date": today_date})
    if reservation.start_time and reservation.end_time:
        initial = {
            "start_time": reservation.start_time,
            "end_time": reservation.end_time,
        }
    else:
        initial = None
    time_form = forms.TimeSelectForm(initial=initial)
    calendars = generate_calendars(today_date)
    start_date = reservation.stay.start_date if reservation.stay.start_date else None
    end_date = reservation.stay.end_date if reservation.stay.end_date else None
    start_time = reservation.stay.start_time if reservation.stay.start_time else None
    end_time = reservation.stay.end_time if reservation.stay.end_time else None
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
                start_date, end_date = reservation.set_dates(selected_date)
        if "select_time" in request.POST:
            time_form = forms.TimeSelectForm(request.POST)
            if time_form.is_valid():
                start_time = time_form.cleaned_data["start_time"]
                end_time = time_form.cleaned_data["end_time"]
                reservation.set_times(start_time, end_time)
    context = {
        "calendars": calendars,
        "today_date": today_date,
        "calendar_form": form,
        "time_form": time_form,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
        "reservation": reservation,
    }
    response = TemplateResponse(request, RESERVATION_TEMPLATE, context)
    return trigger_client_event(response, "updateReservationDetails", after="settle")


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
    context = {"contact_information_form": form, "contact_info": contact_info}
    response = TemplateResponse(request, RESERVATION_TEMPLATE, context)
    return trigger_client_event(response, "updateReservationDetails")


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
    response = TemplateResponse(request, RESERVATION_TEMPLATE, context)
    return trigger_client_event(response, "updateReservationDetails", after="settle")


@htmx_form_validate(form_class=ReservationCreateForm)
@for_htmx(use_block_from_params=True)
def reservation_create(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if request.method == "POST":
        if "confirm-reservation" in request.POST:
            response = send_confirmation_email.delay(reservation.id)
            if response:
                reservation.confirm()
                customer, created = Customer.objects.get_or_create(
                    first_name=reservation.first_name,
                    last_name=reservation.last_name,
                    email=reservation.email,
                    phone=reservation.phone,
                )
                del request.session["first_name"]
                del request.session["last_name"]
                del request.session["email"]
                del request.session["phone"]
    return TemplateResponse(
        request,
        "winadmin/reservations/reservation_create.html",
        {"reservation": reservation},
    )


@for_htmx(use_block_from_params=True)
def update_price(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    return TemplateResponse(
        request,
        "winadmin/reservations/reservation_create.html",
        {"reservation": reservation},
    )


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def reservation_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == "POST":
        form = ReservationDetailForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data["status"]
            stay_type = form.cleaned_data["stay_type"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            reservation.stay.status = status
            reservation.stay.stay_type = stay_type
            reservation.stay.start_date = start_date
            reservation.stay.end_date = end_date
            reservation.stay.save()
            reservation.first_name = first_name
            reservation.last_name = last_name
            reservation.email = email
            reservation.save()
            messages.success(request, _("Reservation successfully edited."))
    initial = {
        "status": reservation.stay.status,
        "stay_type": reservation.stay.stay_type,
        "start_date": reservation.stay.start_date,
        "end_date": reservation.stay.end_date,
        "first_name": reservation.first_name,
        "last_name": reservation.last_name,
        "email": reservation.email,
        "options": reservation.order_items,
    }
    form = ReservationDetailForm(initial=initial)
    return trigger_client_event(
        TemplateResponse(
            request,
            "winadmin/reservations/reservation_detail.html",
            {"form": form, "reservation": reservation},
        ),
        "getMessages",
    )


def get_client():
    client = Client(access_token=SQUARE_ACCESS_TOKEN, environment=SQUARE_ENVIRONMENT)
    return client


def get_or_create_customer(reservation):
    customer, created = Customer.objects.get_or_create(
        first_name=reservation.contact_info.first_name,
        last_name=reservation.contact_info.last_name,
        email=reservation.contact_info.email,
        phone=reservation.contact_info.phone,
    )
    customer.save()
    return customer, created


@for_htmx(use_block_from_params=True)
def make_payment(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if request.method == "POST":
        form = SquarePaymentTokenForm(request.POST)
        token = None
        if form.is_valid():
            token = form.cleaned_data["token"]
        session = {"purchase_amount": 1000}
        body = {
            "source_id": token,
            "idempotency_key": str(uuid.uuid4()),
            "amount_money": {
                "amount": session["purchase_amount"],
                "currency": SQUARE_CURRENCY,
            },
            "autocomplete": True,
            "location_id": SQUARE_LOCATION_ID,
            "note": "Brief description",
        }
        client = get_client()
        payments_api = client.payments
        payment = payments_api.create_payment(body=body)
        if payment.is_success():
            get_or_create_customer(reservation)
            send_confirmation_email(reservation)
            reservation.set_status("reserved")
            context = {"payment": payment}
            return TemplateResponse(
                request, "winadmin/reservations/reservation_create.html", context
            )
    form = SquarePaymentTokenForm()
    context = {
        "form": form,
        "reservation": reservation,
        "SQUARE_APPLICATION_ID": SQUARE_APPLICATION_ID,
        "SQUARE_LOCATION_ID": SQUARE_LOCATION_ID,
        "SQUARE_CURRENCY": SQUARE_CURRENCY,
    }
    return TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )


# def send_confirmation_email(reservation):
#     def format_message(name, email, message):
#         return f"{name}\n{email}\n\n{message}"
#
#     def format_subject(name, email):
#         return f"[KILLIAN.arts] {name}, {email}"
#
#     sender_name = (
#         f"{reservation.contact_info.first_name} {reservation.contact_info.last_name}"
#     )
#     sender_email = f"{reservation.contact_info.email}"
#     message = f"Reservation Details are here! {reservation.stay.start_datetime.strftime('%Y-%m-%d')}"
#     formatted_subject = format_subject(sender_name, sender_email)
#     formatted_message = format_message(sender_name, sender_email, message)
#     send_mail(
#         formatted_subject,
#         formatted_message,
#         "noreply@winvillage.jp",
#         [sender_email],
#     )
