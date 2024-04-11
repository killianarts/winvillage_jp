import calendar
import csv
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pendulum
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory, modelformset_factory
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import activate, deactivate
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event, HttpResponseClientRedirect
from square.client import Client

from core.models import Item, Category, Transaction, Customer
from core.utils import (
    HtmxHttpRequest,
    get_or_set_reservation_session,
    for_htmx,
    htmx_form_validate,
)
from reservations import forms
from reservations.forms import DateForm
from reservations.models import (
    Reservation,
    Stay,
    Room,
    PricingTier,
    PricingTierGroup,
    Campaign,
    RoomTier,
)
from reservations.tasks import send_confirmation_email
from reservations.utils import (
    generate_calendars,
    get_previous_month,
    get_next_month,
)
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
    RoomDetailForm,
    RoomCreateForm,
    PricingTierDetailForm,
    PricingTierCreateForm,
    PricingTierGroupCreateForm,
    PricingTierGroupDetailForm,
    IncrementalPricingTierFormSet,
    CampaignCreateForm,
    CampaignDetailForm,
    RoomTierCreateForm,
    RoomTierDetailForm,
)
from winadmin.models import SpecialDate
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
    return TemplateResponse(request, "winadmin/index.html", {})


@login_required(login_url="winadmin:login_page")
def inventory_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from inventory."}
    )


@login_required(login_url="winadmin:login_page")
def sale_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from sales."}
    )


@htmx_form_validate(form_class=LoginForm)
def login_page(request: HtmxHttpRequest) -> HttpResponse:
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
                messages.error(
                    request=request, message=_("There was an error logging in.")
                )
    context = {"form": form}
    return TemplateResponse(request, "winadmin/login_page.html", context)


@htmx_form_validate(form_class=LoginForm)
def login_page(request: HtmxHttpRequest) -> HttpResponse:
    if request.method != "POST":
        form = LoginForm()
        context = {"form": form}
        return TemplateResponse(request, "winadmin/login_page.html", context)

    form = LoginForm(request.POST)
    if not form.is_valid():
        context = {"form": form}
        return TemplateResponse(request, "winadmin/login_page.html", context)

    username = form.cleaned_data["username"]
    password = form.cleaned_data["password"]
    user = authenticate(request, username=username, password=password)
    if user is None:
        messages.error(request=request, message=_("There was an error logging in."))
        context = {"form": form}
        return TemplateResponse(request, "winadmin/login_page.html", context)

    login(request, user)
    return redirect("winadmin:index")


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
            messages.error(request, _("Input category name"))
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


@login_required(login_url="winadmin:login_page")
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
        if "edit" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request, _("Item Successfully Edited"))
            else:
                messages.error(request, _("Error"))
        if "delete" in request.POST:
            if form.is_valid():
                item.delete()
                messages.success(request, _("Item Successfully Edited"))
                return HttpResponseClientRedirect(reverse("winadmin:item_list"))
            else:
                messages.error(request, _("Error"))
    response = TemplateResponse(
        request, "winadmin/inventory/item_detail.html", {"form": form, "item": item}
    )
    return trigger_client_event(
        response=response,
        name="getMessages",
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
    return HttpResponseClientRedirect(reverse("winadmin:list_inventory"))


# Transactions


@login_required(login_url="winadmin:login_page")
def sale_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    return _sales_list_by_period(request)


def get_current_year_and_month(request, tz=TIMEZONE):
    active_timezone = activate(tz)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    deactivate()
    return year, month


def get_balance_and_ledger(transactions: Transaction):
    balance = 0
    ledger = []
    for transaction in transactions:
        if transaction.name == "sale":
            balance += transaction.total_price_rounded
        elif transaction.name == "return" or transaction.name == "purchase":
            balance -= transaction.total_price_rounded
        ledger.append([transaction, balance])
    return balance, ledger


@login_required(login_url="winadmin:login_page")
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
    if "get_item_price" in request.GET:
        item = Item.objects.get()
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
    if request.GET.get("action") == "filter":
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
def transaction_export_csv_by_period(request) -> HttpResponse:
    form = SetLedgerPeriodForm(request.GET)
    if form.is_valid():
        year = form.cleaned_data["year"]
        month = form.cleaned_data["month"]
        transactions = Transaction.objects.filter(
            transaction_datetime__year=year
        ).filter(transaction_datetime__month=month)
        balance, ledger = get_balance_and_ledger(transactions)
        response = HttpResponse(content_type="text/csv")
        filename = f"transactions_{year}_{month}.csv"
        path = f"csv/{filename}"
        response["Content-Disposition"] = f"attachment; filename={filename}"

        # TODO: Check that a file exactly matching
        # if os.path.exists(path):
        #     return response

        with open(path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    _("Name"),
                    _("Customer"),
                    _("Date"),
                    _("Item"),
                    _("Quantity"),
                    _("Total Price"),
                    _("Balance"),
                ]
            )
            for transaction, balance in ledger:
                writer.writerow(
                    [
                        transaction.name,
                        transaction.customer,
                        transaction.transaction_datetime.date(),
                        transaction.item.name,
                        transaction.quantity,
                        transaction.total_price_rounded,
                        balance,
                    ]
                )

        with open(path, "r") as csvfile:
            response.write(csvfile.read())

        return response


@login_required(login_url="winadmin:login_page")
def transaction_detail(request: HtmxHttpRequest, id: int) -> HttpResponse:
    transaction = Transaction.objects.get(id=id)
    form = TransactionCreateForm(instance=transaction)
    if request.method == "POST":
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.INFO, _("Transaction Created Successfully")
            )
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


@login_required(login_url="winadmin:login_page")
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
        initial["start_date"] = reservation.stay.start_date
        initial["end_date"] = reservation.stay.end_date
    grills = reservation.get_grills()
    if request.method == "POST":
        form = ReservationCreateForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            if not reservation.stay:
                stay = Stay.objects.create(
                    start_date=start_date,
                    end_date=end_date,
                )
                reservation.stay = stay
                reservation.save()
            else:
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
                selected_date = pendulum.instance(
                    calendar_cell_form.cleaned_data["date"]
                )
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


@login_required(login_url="winadmin:login_page")
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
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            reservation.stay.status = status
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


@login_required(login_url="winadmin:login_page")
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


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def room_create(request: HtmxHttpRequest) -> HttpResponse:
    room_create_form = RoomCreateForm()
    if request.method == "POST":
        if "create-room" in request.POST:
            room_create_form = RoomCreateForm(request.POST)
            if room_create_form.is_valid():
                instance = room_create_form.save()
                messages.success(request, f"{ instance } successfully created")
                room_create_form = RoomCreateForm()
            else:
                messages.error(request, "Error!")
    context = {"room_create_form": room_create_form}
    response = TemplateResponse(request, "winadmin/room_create.html", context)
    return trigger_client_event(response=response, name="getMessages")


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def room_list(request: HtmxHttpRequest) -> HttpResponse:
    rooms = Room.objects.all()
    if "filter" in request.GET:
        filters = request.GET.getlist("filter", default=None)
        # for filter in filters:
        # Insert Filters Here
        # rooms = Room.objects.filter()
    context = {"rooms": rooms}
    return TemplateResponse(request, "winadmin/room_list.html", context)


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def room_detail(request: HtmxHttpRequest, room_id: int) -> HttpResponse:
    room = get_object_or_404(Room, id=room_id)
    form = RoomDetailForm(instance=room)
    if request.method == "POST":
        form = RoomDetailForm(request.POST, instance=room)
        if "edit" in request.POST:
            if form.is_valid():
                instance = form.save()
                messages.success(request, _("Room successfully edited"))
            else:
                messages.error(request, _("Couldn't edit room"))
        if "delete" in request.POST:
            room.delete()
            messages.success(request, _("Room deleted successfully"))
            return HttpResponseClientRedirect(reverse("winadmin:room_list"))
    context = {"form": form}
    response = TemplateResponse(request, "winadmin/room_detail.html", context)
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def room_tier_create(request: HtmxHttpRequest) -> HttpResponse:
    form = RoomTierCreateForm()
    if request.method == "POST":
        form = RoomTierCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(request, "Success!")
        else:
            messages.error(request, "Error!")
    context = {"form": form}
    response = TemplateResponse(request, "winadmin/room_tier_create.html", context)
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def room_tier_list(request: HtmxHttpRequest) -> HttpResponse:
    room_tiers = RoomTier.objects.all()
    if "filter" in request.GET:
        filters = request.GET.getlist("filter", default=None)
        # for filter in filters:
        # Insert Filters Here
        # room_tiers = RoomTier.objects.filter()
    context = {"room_tiers": room_tiers}
    return TemplateResponse(request, "winadmin/room_tier_list.html", context)


@for_htmx(use_block_from_params=True)
def room_tier_detail(request: HtmxHttpRequest, room_tier_id: int) -> HttpResponse:
    room_tier = get_object_or_404(RoomTier, id=room_tier_id)
    form = RoomTierDetailForm(instance=room_tier)
    if request.method == "POST":
        form = RoomTierDetailForm(request.POST, instance=room_tier)
        if "edit" in request.POST:
            if form.is_valid():
                instance = form.save()
                messages.success(request, "Success!")
            else:
                messages.error(request, "Error!")
        if "delete" in request.POST:
            room_tier.delete()
            messages.success(request, "Success!")
            return HttpResponseClientRedirect(reverse("winadmin:room_tier_list"))
    context = {"form": form}
    response = TemplateResponse(request, "winadmin/room_tier_detail.html", context)
    return trigger_client_event(response=response, name="getMessages")


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def pricing_tier_create(request: HtmxHttpRequest) -> HttpResponse:
    form = PricingTierCreateForm()
    if request.method == "POST":
        form = PricingTierCreateForm(request.POST)
        if form.is_valid():
            form.save()
            tier_name = form.cleaned_data["name"]
            messages.success(
                request,
                _("%(tier_name)s Created Successfully!") % {"tier_name": tier_name},
            )
        else:
            messages.error(request, "Error!")
    context = {"form": form}
    response = TemplateResponse(request, "winadmin/pricing_tier_create.html", context)
    return trigger_client_event(response, "getMessages")


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def pricing_tier_list(request: HtmxHttpRequest) -> HttpResponse:
    pricing_tiers = PricingTier.objects.all()
    if "filter" in request.GET:
        filters = request.GET.getlist("filter", default=None)
        # for filter in filters:
        # Insert Filters Here
        # pricing_tiers = PricingTier.objects.filter()
    context = {"pricing_tiers": pricing_tiers}
    return TemplateResponse(request, "winadmin/pricing_tier_list.html", context)


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def pricing_tier_detail(request: HtmxHttpRequest, pricing_tier_id: int) -> HttpResponse:
    pricing_tier = get_object_or_404(PricingTier, id=pricing_tier_id)
    form = PricingTierDetailForm(instance=pricing_tier)
    if request.method == "POST":
        form = PricingTierDetailForm(request.POST, instance=pricing_tier)
        if "edit" in request.POST:
            if form.is_valid():
                instance = form.save()
                messages.success(request, f"{instance.name} edited successfully.")
            else:
                messages.error(request, "Error!")
        if "delete" in request.POST:
            if form.is_valid():
                pricing_tier.delete()
                messages.success(request, "Success!")
                return HttpResponseClientRedirect(reverse("winadmin:pricing_tier_list"))
    context = {"form": form}
    response = TemplateResponse(request, "winadmin/pricing_tier_detail.html", context)
    return trigger_client_event(response, "getMessages")


@login_required(login_url="winadmin:login_page")
def test_pricing_tiers(request):
    return TemplateResponse(
        request=request, template="winadmin/reservations/test.html", context={}
    )


@login_required(login_url="winadmin:login_page")
def recurrence(request):
    cal = calendar.Calendar()
    the_month = pendulum.today().date().start_of("month")
    last_month = the_month.subtract(months=1)
    the_next_month = the_month.add(months=1)
    current_calendar = cal.itermonthdates(the_month.year, the_month.month)
    next_calendar = cal.itermonthdates(the_next_month.year, the_next_month.month)
    weekends = SpecialDate.objects.get(name="Weekend").recurrence.between(
        last_month, the_next_month, dtstart=last_month
    )
    weekends = [day.date() for day in weekends]
    calendars = {"selected_month": current_calendar, "next_month": next_calendar}
    return TemplateResponse(
        request=request,
        template="winadmin/reservations/recurrence.html",
        context={"calendars": calendars, "weekends": weekends},
    )


# @for_htmx(use_block_from_params=True)
# def pricing_tier_group_create(request: HtmxHttpRequest) -> HttpResponse:
#     form = PricingTierGroupCreateForm()
#     formset = PricingTierFormSet()
#     if request.method == "POST":
#         form = PricingTierGroupCreateForm(request.POST)
#         formset = PricingTierFormSet(request.POST)
#         if "submit" in request.POST:
#             if form.is_valid() and formset.is_valid():
#                 group_obj = PricingTierGroup()
#                 group = group_obj.create_group(form=form, formset=formset)
#                 messages.success(request, f"Group {group.name} created successfully.")
#                 form = PricingTierGroupCreateForm()
#                 formset = PricingTierFormSet()
#             else:
#                 messages.error(request, "Error!")
#     context = {"form": form, "formset": formset}
#     return TemplateResponse(
#         request, "reservations/pricing_tier_group_create.html", context
#     )


@for_htmx(use_block_from_params=True)
def pricing_tier_group_create(request: HtmxHttpRequest) -> HttpResponse:
    min_adults = int(
        request.GET.get("min_adults") or request.POST.get("min_adults") or 1
    )
    max_adults = int(
        request.GET.get("max_adults") or request.POST.get("max_adults") or 6
    )
    num_extras = max_adults - min_adults + 1
    PricingTierFormSet = inlineformset_factory(
        parent_model=PricingTierGroup,
        model=PricingTier,
        form=PricingTierCreateForm,
        formset=IncrementalPricingTierFormSet,
        extra=num_extras,
        can_delete=False,
    )
    form = PricingTierGroupCreateForm(
        initial={"min_adults": min_adults, "max_adults": max_adults}
    )
    formset = PricingTierFormSet(min_adults=min_adults, max_adults=max_adults)
    if request.method == "POST":
        form = PricingTierGroupCreateForm(request.POST)
        formset = PricingTierFormSet(request.POST, request.FILES)
        if "submit" in request.POST:
            if form.is_valid() and formset.is_valid():
                group_obj = PricingTierGroup()
                group = group_obj.create_group(form=form, formset=formset)
                messages.success(request, f"Group {group.name} created successfully.")
                form = PricingTierGroupCreateForm(
                    initial={"min_adults": min_adults, "max_adults": max_adults}
                )
                formset = PricingTierFormSet(
                    min_adults=min_adults, max_adults=max_adults
                )
            else:
                messages.error(request, "Error!")
    context = {"form": form, "formset": formset}
    response = TemplateResponse(
        request, "reservations/pricing_tier_group_create.html", context
    )
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def pricing_tier_group_list(request: HtmxHttpRequest) -> HttpResponse:
    pricing_tier_groups = PricingTierGroup.objects.all()
    if "filter" in request.GET:
        filters = request.GET.getlist("filter", default=None)
        # for filter in filters:
        # Insert Filters Here
        # pricing_tier_groups = PricingTierGroup.objects.filter()
    context = {"pricing_tier_groups": pricing_tier_groups}
    return TemplateResponse(
        request, "reservations/pricing_tier_group_list.html", context
    )


@for_htmx(use_block_from_params=True)
def pricing_tier_group_detail(
    request: HtmxHttpRequest, pricing_tier_group_id: int
) -> HttpResponse:
    pricing_tier_group = get_object_or_404(PricingTierGroup, id=pricing_tier_group_id)
    PricingTierFormSet = modelformset_factory(
        model=PricingTier,
        fields=("number_of_adults", "price_overnight", "price_short_term"),
        extra=0,
    )

    initial = {
        "name": pricing_tier_group.name,
        "min_adults": pricing_tier_group.minimum_number_of_adults,
        "max_adults": pricing_tier_group.maximum_number_of_adults,
        "room_tiers": pricing_tier_group.room_tiers.all(),
        "campaigns": pricing_tier_group.campaigns.all(),
    }
    min_adults = int(
        request.GET.get("min_adults")
        or request.POST.get("min_adults")
        or pricing_tier_group.minimum_number_of_adults
    )
    max_adults = int(
        request.GET.get("max_adults")
        or request.POST.get("max_adults")
        or pricing_tier_group.maximum_number_of_adults
    )
    form = PricingTierGroupDetailForm(initial=initial)
    queryset = PricingTier.objects.filter(tier_group=pricing_tier_group)
    formset = PricingTierFormSet(queryset=queryset)

    if request.method == "POST":
        form = PricingTierGroupDetailForm(request.POST, instance=pricing_tier_group)
        formset = PricingTierFormSet(request.POST, request.FILES, queryset=queryset)
        if "edit" in request.POST:
            if form.is_valid() and formset.is_valid():
                group = pricing_tier_group.edit_group(form=form, formset=formset)
                messages.success(request, f"Group {group.name} edited successfully.")
            else:
                messages.error(request, "Error!")
        elif "delete" in request.POST:
            group_name = pricing_tier_group.name
            pricing_tier_group.delete()
            messages.success(request, f"Group {group_name} deleted successfully.")
            return HttpResponseClientRedirect(
                reverse("winadmin:pricing_tier_group_list")
            )
    context = {"form": form, "formset": formset}
    response = TemplateResponse(
        request, "reservations/pricing_tier_group_detail.html", context
    )
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def campaign_create(request: HtmxHttpRequest) -> HttpResponse:
    form = CampaignCreateForm()
    if request.method == "POST":
        form = CampaignCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(request, "Success!")
        else:
            messages.error(request, "Error!")
    context = {"form": form}
    response = TemplateResponse(request, "campaign/campaign_create.html", context)
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def campaign_list(request: HtmxHttpRequest) -> HttpResponse:
    campaigns = Campaign.objects.all()
    # if "filter" in request.GET:
    #     filters = request.GET.getlist("filter", default=None)
    #     for filter in filters:
    # campaigns = Campaign.objects.filter()
    context = {"campaigns": campaigns}
    return TemplateResponse(request, "campaign/campaign_list.html", context)


@for_htmx(use_block_from_params=True)
def campaign_detail(request: HtmxHttpRequest, campaign_id: int) -> HttpResponse:
    campaign = get_object_or_404(Campaign, id=campaign_id)
    form = CampaignDetailForm(instance=campaign)
    if request.method == "POST":
        form = CampaignDetailForm(request.POST, instance=campaign)
        if "edit" in request.POST:
            if form.is_valid():
                instance = form.save()
                messages.success(request, "Success!")
            else:
                messages.error(request, "Error!")
        if "delete" in request.POST:
            campaign.delete()
            messages.success(request, "Success!")
            return HttpResponseClientRedirect(reverse("winadmin:campaign_list"))
    context = {"form": form}
    response = TemplateResponse(request, "campaign/campaign_detail.html", context)
    return trigger_client_event(response=response, name="getMessages")
