import csv
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import pendulum
from core.accounting_utils import (
    get_accounts_receivable_account_from_configuration,
    get_cash_account_from_configuration,
    get_inventory_account_from_configuration,
    get_sales_account_from_configuration,
)
from core.models import (
    Category,
    Customer,
    Invoice,
    Item,
    Procurement,
    TransactionDetail,
    Vendor,
)
from core.utils import (
    HtmxHttpRequest,
    for_htmx,
    get_or_set_reservation_session,
    htmx_form_validate,
)
from django.contrib import messages
from django.forms import inlineformset_factory, modelformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import activate, deactivate, get_default_timezone
from django.utils.translation import gettext_lazy as _
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event
from djmoney.money import Money
from hordak.models import Account
from hordak.models import Account as BusinessAccount
from hordak.models import Leg
from hordak.models import Transaction
from hordak.models import Transaction as BusinessTransaction
from reservations import forms
from reservations.forms import DateForm
from reservations.models import (
    Campaign,
    PricingTier,
    PricingTierGroup,
    Reservation,
    Room,
    RoomTier,
    Stay,
)
from reservations.tasks import send_confirmation_email
from reservations.utils import (
    generate_calendars,
    generate_campaign_calendars,
    get_next_month,
    get_previous_month,
    make_pen,
)
from square.client import Client
from winvillage import settings
from winvillage.settings import TIME_ZONE

from winadmin.forms import (
    AccountForm,
    CampaignCreateForm,
    CampaignDetailForm,
    CategoryCreateForm,
    CategoryDetailForm,
    CompanyWiseProcurementLedgerFilter,
    IncrementalPricingTierFormSet,
    InvoiceCreateForm,
    InvoiceDetailForm,
    ItemCreateForm,
    ItemEditForm,
    PricingTierCreateForm,
    PricingTierDetailForm,
    PricingTierGroupCreateForm,
    PricingTierGroupDetailForm,
    ProcurementCreateForm,
    ProcurementDetailForm,
    ReservationCreateForm,
    ReservationDetailForm,
    RoomCreateForm,
    RoomDetailForm,
    RoomTierCreateForm,
    RoomTierDetailForm,
    SetLedgerPeriodForm,
    SetReservationPeriodForm,
    SimpleTransactionForm,
    SquarePaymentTokenForm,
    VendorCreateForm,
    VendorDetailForm,
)

SQUARE_APPLICATION_ID = settings.SQUARE_SETTINGS["SQUARE_APPLICATION_ID"]
SQUARE_LOCATION_ID = settings.SQUARE_SETTINGS["SQUARE_LOCATION_ID"]
SQUARE_CURRENCY = settings.SQUARE_SETTINGS["SQUARE_CURRENCY"]
SQUARE_ACCESS_TOKEN = settings.SQUARE_SETTINGS["SQUARE_ACCESS_TOKEN"]
SQUARE_ENVIRONMENT = settings.SQUARE_SETTINGS["SQUARE_ENVIRONMENT"]

TIMEZONE = "Asia/Tokyo"


# Index and Login


def index(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(request, "winadmin/index.html", {})


def inventory_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from inventory."}
    )


def sale_management_page(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(
        request, "winadmin/index.html", {"greeting": "Hello from sales."}
    )


# Inventory


def item_list(request: HtmxHttpRequest) -> HttpResponse:
    items = Item.objects.all().order_by("name")
    context = {"items": items}
    return TemplateResponse(request, "winadmin/inventory/item_list.html", context)


@for_htmx(use_block_from_params=True)
def item_create(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        if "submit" in request.POST:
            form = ItemCreateForm(request.POST, request.FILES)
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


@htmx_form_validate(form_class=ItemEditForm)
@for_htmx(use_block_from_params=True)
def item_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item.objects.all(), pk=pk)
    form = ItemEditForm(instance=item)
    if request.method == "POST":
        form = ItemEditForm(request.POST, request.FILES, instance=item)
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


# Transactions
# TODO: Reimplement these using Hordak Transactions/Accounts


def get_current_year_and_month(request, tz=TIMEZONE):
    active_timezone = activate(tz)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    deactivate()
    return year, month


def get_balance_and_ledger(transactions):
    balance = 0
    ledger = []
    for transaction in transactions:
        if transaction.name == "sale":
            balance += transaction.total_price
        elif transaction.name == "return" or transaction.name == "purchase":
            balance -= transaction.total_price
        ledger.append([transaction, balance])
    return balance, ledger


@for_htmx(use_block_from_params=True)
def sales_ledger(request: HtmxHttpRequest) -> HttpResponse:
    account = get_sales_account_from_configuration()
    sales_legs = Leg.objects.filter(account=account)
    details = TransactionDetail.objects.filter(summary__legs__in=sales_legs)
    year, month = get_current_year_and_month(request)
    if request.GET.get("action") == "filter":
        form = SetLedgerPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
        details = details.filter(summary__date__year=year, summary__date__month=month)
    else:
        form = SetLedgerPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    context = {
        "account": account,
        "details": details,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(request, "winadmin/sales/sales_ledger.html", context)


@for_htmx(use_block_from_params=True)
def accounts_receivable_ledger(request):
    account = get_accounts_receivable_account_from_configuration()
    receivable_legs = Leg.objects.filter(account=account)
    details = TransactionDetail.objects.filter(summary__legs__in=receivable_legs)
    year, month = get_current_year_and_month(request)
    if request.GET.get("action") == "filter":
        form = SetLedgerPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
        details = details.filter(summary__date__year=year, summary__date__month=month)
    else:
        form = SetLedgerPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    context = {
        "account": account,
        "details": details,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/sales/accounts_receivable_ledger.html", context
    )


@for_htmx(use_block_from_params=True)
def transaction_create(request: HtmxHttpRequest) -> HttpResponse:
    item_id = request.GET.get("item", default=None)
    quantity = int(request.GET.get("quantity", default=1))
    if item_id:
        item_price = Item.objects.get(id=item_id).price
        total_price = item_price * quantity
    else:
        total_price = 0
    initial = {"item": item_id, "quantity": quantity, "total_price": total_price}
    form = TransactionCreateForm(initial=initial)
    if request.method == "POST":
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Transaction Created Successfully"))
        elif not form.is_valid():
            messages.error(request, _("Transaction Couldn't Be Created"))
    context = {"form": form}
    return trigger_client_event(
        TemplateResponse(
            request, "winadmin/transactions/transaction_create.html", context
        ),
        "getMessages",
    )


@for_htmx(use_block_from_params=True)
def transaction_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    account = get_sales_account_from_configuration()
    details = TransactionDetail.objects.all()
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
    context = {
        "account": account,
        "details": details,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/sales/sales_list_by_period.html", context
    )


@for_htmx(use_block_from_params=True)
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
                        transaction.get_name_display(),
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


@for_htmx(use_block_from_params=True)
def transaction_detail(request: HtmxHttpRequest, id: int) -> HttpResponse:
    transaction = Transaction.objects.get(id=id)
    item_price = transaction.price_per_unit
    total_price = transaction.total_price
    form = TransactionCreateForm(instance=transaction)
    if request.method == "POST":
        form = TransactionCreateForm(request.POST, instance=transaction)
        if "edit" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request, _("Transaction Edited Successfully"))
        if "delete" in request.POST:
            transaction.delete()
            messages.success(request, _("Transaction Deleted Successfully"))
            return HttpResponseClientRedirect(
                reverse("winadmin:transaction_list_by_period")
            )
    context = {"form": form}
    response = TemplateResponse(
        request, "winadmin/transactions/transaction_detail.html", context
    )
    return trigger_client_event(response=response, name="getMessages")


# Reservations


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
            # reservation.first_name = form.cleaned_data["first_name"]
            # reservation.last_name = form.cleaned_data["last_name"]
            # reservation.email = form.cleaned_data["email"]
            # reservation.phone = form.cleaned_data["phone"]
            # reservation.save()
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


# @htmx_form_validate(form_class=ReservationCreateForm)
@for_htmx(use_block_from_params=True)
def reservation_create(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if request.method == "POST":
        if "confirm-reservation" in request.POST:
            customer, created = Customer.objects.get_or_create(
                first_name=request.session["first_name"],
                last_name=request.session["last_name"],
                email=request.session["email"],
                phone=request.session["phone"],
            )
            reservation.customer = customer
            reservation.confirm()
            response = send_confirmation_email.delay(reservation.id)
    return TemplateResponse(
        request,
        "winadmin/reservations/reservation_create.html",
        {"reservation": reservation},
    )


@for_htmx(use_block_from_params=True)
def reservation_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    reservations = (
        Reservation.objects.select_related("stay")
        .exclude(stay__status="not_reserved")
        .order_by("stay__start")
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
    reservations = reservations.filter(stay__start__year=year, stay__start__month=month)
    context = {
        "reservations": reservations,
        "year": year,
        "month": month,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/reservations/reservation_list_by_period.html", context
    )


@for_htmx(use_block_from_params=True)
def update_price(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    return TemplateResponse(
        request,
        "winadmin/reservations/reservation_create.html",
        {"reservation": reservation},
    )


@for_htmx(use_block_from_params=True)
def reservation_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == "POST":
        form = ReservationDetailForm(request.POST)
        if form.is_valid():
            status = form.cleaned_data["status"]
            price = form.cleaned_data["price"]
            start_date = form.cleaned_data["start"]
            end_date = form.cleaned_data["end"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]
            reservation.stay.status = status
            reservation.stay.status = status
            reservation.stay.start_date = start_date
            reservation.stay.end_date = end_date
            reservation.stay.save()
            reservation.customer.first_name = first_name
            reservation.customer.last_name = last_name
            reservation.customer.email = email
            reservation.customer.phone = phone
            reservation.save()
            messages.success(request, _("Reservation successfully edited."))
    initial = {
        "status": reservation.stay.status,
        "price": reservation.get_price(),
        "start": reservation.stay.start,
        "end": reservation.stay.end,
        "first_name": reservation.customer.first_name,
        "last_name": reservation.customer.last_name,
        "email": reservation.customer.email,
        "phone": reservation.customer.phone,
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


@for_htmx(use_block_from_params=True)
def customer_check_in_check_out_list(request: HtmxHttpRequest):
    reservations = (
        Reservation.objects.select_related("stay")
        .exclude(stay__status__in=["not_reserved", "cancelled"])
        .order_by("stay__start")
    )
    active_timezone = activate(TIMEZONE)
    year = request.GET.get("year", pendulum.now(tz=TIMEZONE).year)
    month = request.GET.get("month", pendulum.now(tz=TIMEZONE).month)
    day = request.GET.get("day", pendulum.now(tz=TIMEZONE).day)
    deactivate()
    form = SetReservationPeriodForm(initial={"year": year, "month": month, "day": day})
    reservations = reservations.filter(
        stay__start__year=year, stay__start__month=month, stay__start__day=day
    )
    context = {
        "reservations": reservations,
        "year": year,
        "month": month,
        "day": day,
        "form": form,
    }
    return TemplateResponse(
        request, "winadmin/reservations/customer_check_in_check_out_list.html", context
    )


@for_htmx(use_block_from_params=True)
def customer_check_in_check_out_detail(request: HtmxHttpRequest, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    if request.method == "POST":
        if "check-in-with-cash" in request.POST:
            if not reservation.stay.status == "checked_in":
                reservation.check_in()
                sales_account = get_sales_account_from_configuration()
                cash_account = get_cash_account_from_configuration()
                detail = TransactionDetail.sales.create(
                    to_account=cash_account,
                    amount=reservation.get_price(),
                    item="Reservation",
                    quantity=1,
                    price_per_unit=reservation.get_price(),
                )
                detail.save()
                messages.success(request, _(f"{reservation.customer} checked-in."))
            else:
                messages.error(
                    request, _(f"{reservation.customer} is already checked-in.")
                )
        if "check-in-with-card" in request.POST:
            if not reservation.stay.status == "checked_in":
                reservation.check_in()
                sales_account = get_sales_account_from_configuration()
                cash_account = get_cash_account_from_configuration()
                detail = TransactionDetail.sales.create(
                    to_account=cash_account,
                    amount=reservation.get_price(),
                    item="Reservation",
                    quantity=1,
                    price_per_unit=reservation.get_price(),
                )
                detail.save()
            else:
                messages.error(
                    request, _(f"{reservation.customer} is already checked-in.")
                )

        if "check-out" in request.POST:
            if reservation.stay.status == "checked_in":
                reservation.check_out()
                messages.success(request, _(f"{reservation.customer} checked-out."))
            else:
                messages.error(
                    request, _(f"{reservation.customer} is already checked-out.")
                )
    context = {
        "reservation": reservation,
    }
    response = TemplateResponse(
        request,
        "winadmin/reservations/customer_check_in_check_out_detail.html",
        context,
    )
    return trigger_client_event(response, "getMessages")


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


# Rooms


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


# Pricing Tiers


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


@for_htmx(use_block_from_params=True)
def pricing_tier_group_create(request: HtmxHttpRequest) -> HttpResponse:
    minimum_number_of_adults = int(
        request.GET.get("minimum_number_of_adults")
        or request.POST.get("minimum_number_of_adults")
        or 1
    )
    maximum_number_of_adults = int(
        request.GET.get("maximum_number_of_adults")
        or request.POST.get("maximum_number_of_adults")
        or 6
    )
    num_extras = maximum_number_of_adults - minimum_number_of_adults + 1
    PricingTierFormSet = inlineformset_factory(
        parent_model=PricingTierGroup,
        model=PricingTier,
        form=PricingTierCreateForm,
        formset=IncrementalPricingTierFormSet,
        extra=num_extras,
        can_delete=False,
    )
    form = PricingTierGroupCreateForm(
        initial={
            "minimum_number_of_adults": minimum_number_of_adults,
            "maximum_number_of_adults": maximum_number_of_adults,
        }
    )
    formset = PricingTierFormSet(
        minimum_number_of_adults=minimum_number_of_adults,
        maximum_number_of_adults=maximum_number_of_adults,
    )
    if request.method == "POST":
        form = PricingTierGroupCreateForm(request.POST)
        formset = PricingTierFormSet(request.POST, request.FILES)
        if "submit" in request.POST:
            if form.is_valid():
                if formset.is_valid():
                    group_obj = PricingTierGroup()
                    group = group_obj.create_group(form=form, formset=formset)
                    messages.success(
                        request, f"Group {group.name} created successfully."
                    )
                    form = PricingTierGroupCreateForm(
                        initial={
                            "minimum_number_of_adults": minimum_number_of_adults,
                            "maximum_number_of_adults": maximum_number_of_adults,
                        }
                    )
                    formset = PricingTierFormSet(
                        minimum_number_of_adults=minimum_number_of_adults,
                        maximum_number_of_adults=maximum_number_of_adults,
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
    today_date = pendulum.today()
    date_filter_form = forms.DateTimeForm(initial={"datetime": today_date})
    initial = {
        "name": pricing_tier_group.name,
        "minimum_number_of_adults": pricing_tier_group.minimum_number_of_adults,
        "maximum_number_of_adults": pricing_tier_group.maximum_number_of_adults,
        "room_tiers": pricing_tier_group.room_tiers.all(),
        "campaign": pricing_tier_group.campaign,
    }
    PricingTierFormSet = modelformset_factory(
        model=PricingTier,
        fields=("number_of_adults", "price_overnight", "price_short_term"),
        extra=0,
    )
    form = PricingTierGroupDetailForm(initial=initial)
    queryset = PricingTier.objects.filter(tier_group=pricing_tier_group)
    formset = PricingTierFormSet(queryset=queryset)
    if request.method == "GET":
        if "get_previous_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_previous_month(datetime)
                date_filter_form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_campaign_calendars(
                    campaign=pricing_tier_group.campaign, date_=datetime
                )
        elif "get_next_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_next_month(datetime)
                date_filter_form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_campaign_calendars(
                    campaign=pricing_tier_group.campaign, date_=datetime
                )
        else:
            calendars = generate_campaign_calendars(
                campaign=pricing_tier_group.campaign, date_=today_date
            )
    if request.method == "POST":
        form = PricingTierGroupDetailForm(request.POST, instance=pricing_tier_group)
        formset = PricingTierFormSet(request.POST, request.FILES, queryset=queryset)
        if "edit" in request.POST:
            if form.is_valid() and formset.is_valid():
                group = pricing_tier_group.edit_group(form=form, formset=formset)
                calendars = generate_campaign_calendars(
                    campaign=pricing_tier_group.campaign, date_=today_date
                )
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
    context = {
        "form": form,
        "formset": formset,
        "date_filter_form": date_filter_form,
        "calendars": calendars,
    }
    response = TemplateResponse(
        request, "reservations/pricing_tier_group_detail.html", context
    )
    return trigger_client_event(response=response, name="getMessages")


# Campaigns


@for_htmx(use_block_from_params=True)
def campaign_create(request: HtmxHttpRequest) -> HttpResponse:
    form = CampaignCreateForm()
    # today_date = pendulum.today()
    # date_filter_form = forms.DateTimeForm(initial={"datetime": today_date})
    # if request.htmx:
    #     form = CampaignCreateForm(request.POST)
    #     if form.is_valid():
    #         campaign = form.save(commit=False)
    #         calendars = generate_campaign_calendars(campaign=campaign)
    #     else:
    #         calendars = generate_campaign_calendars()
    if request.method == "POST":
        form = CampaignCreateForm(request.POST)
        if form.is_valid():
            instance = form.save()
            messages.success(request, "Success!")
        else:
            # calendars = generate_campaign_calendars()
            messages.error(request, "Error!")
    # elif request.method == "GET":
    #     calendars = generate_campaign_calendars()
    context = {
        "form": form,
        # "date_filter_form": date_filter_form,
        # "calendars": calendars
    }
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

    today_date = pendulum.today()
    date_filter_form = forms.DateTimeForm(initial={"datetime": today_date})
    if request.method == "GET":
        if "get_previous_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_previous_month(datetime)
                date_filter_form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_campaign_calendars(
                    campaign=campaign, date_=datetime
                )
        elif "get_next_month" in request.GET:
            form = forms.DateTimeForm(request.GET)
            if form.is_valid():
                datetime = make_pen(form.cleaned_data["datetime"])
                datetime = get_next_month(datetime)
                date_filter_form = forms.DateTimeForm(initial={"datetime": datetime})
                calendars = generate_campaign_calendars(
                    campaign=campaign, date_=datetime
                )
        else:
            calendars = generate_campaign_calendars(campaign=campaign, date_=today_date)

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
    context = {
        "form": form,
        "date_filter_form": date_filter_form,
        "calendars": calendars,
    }
    response = TemplateResponse(request, "campaign/campaign_detail.html", context)
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def vendor_create(request):
    if request.method == "POST":
        form = VendorCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Vendor Created Successfully"))
        else:
            messages.error(request, _("Vendor Couldn't Be Created"))
    else:
        form = VendorCreateForm()

    response = TemplateResponse(request, "vendor/vendor_create.html", {"form": form})
    return trigger_client_event(response, "getMessages")


# TODO Combine vendor_create and business_account_create
# @for_htmx(use_block_from_params=True)
# def vendor_create(request):
#     if request.method == "POST":
#         form = VendorCreateForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, _("Vendor Created Successfully"))
#         else:
#             messages.error(request, _("Vendor Couldn't Be Created"))
#     else:
#         vendor_form = VendorCreateForm()
#         account_form

#     response = TemplateResponse(request, "vendor/vendor_create.html", {"form": form})
#     return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def vendor_list(request):
    vendors = Vendor.objects.all()
    return TemplateResponse(request, "vendor/vendor_list.html", {"vendors": vendors})


@for_htmx(use_block_from_params=True)
def vendor_detail(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    if request.method == "POST":
        form = VendorDetailForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, _("Vendor updated successfully"))
        else:
            messages.error(request, _("Vendor couldn't be updated"))
    else:
        form = VendorCreateForm(instance=vendor)
    response = TemplateResponse(request, "vendor/vendor_create.html", {"form": form})
    return trigger_client_event(response, "getMessages")


# For developers only. The Task is our normal way of making invoices.
@for_htmx(use_block_from_params=True)
def invoice_create(request):
    vendor = get_object_or_404(Vendor, id=1)
    account = Account.objects.get(name=vendor.name)
    if request.method == "POST":
        form = InvoiceCreateForm(request.POST)
        if form.is_valid():
            this_month_cutoff_datetime = vendor.get_cutoff_date(
                pendulum.today().year, pendulum.today().month
            )
            last_month_cutoff_datetime = this_month_cutoff_datetime.subtract(months=1)
            legs = Leg.objects.filter(
                account=account,
                transaction__date__range=(
                    last_month_cutoff_datetime,
                    this_month_cutoff_datetime,
                ),
            )
            procurements = TransactionDetail.objects.filter(summary__legs__in=legs)
            invoice = vendor.create_invoice(this_month_cutoff_datetime, procurements)
            messages.success(request, _("Invoice created successfully"))
        else:
            messages.error(request, _("Invoice couldn't be created"))
    else:
        this_month_cutoff_datetime = vendor.get_cutoff_date(
            pendulum.today().year, pendulum.today().month
        )
        due_date = vendor.get_due_date(this_month_cutoff_datetime)
        initial = {
            "vendor": vendor,
            "invoiced_on": this_month_cutoff_datetime,
            "due_on": due_date,
        }
        form = InvoiceCreateForm(initial=initial)
        invoice = None
    response = TemplateResponse(
        request,
        "invoice/invoice_create.html",
        {
            "form": form,
            "invoice": invoice,
            "this_month_cutoff_datetime": this_month_cutoff_datetime,
        },
    )
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def invoice_list(request):
    invoices = Invoice.objects.all()
    context = {"invoices": invoices}
    return TemplateResponse(request, "invoice/invoice_list.html", context)


@for_htmx(use_block_from_params=True)
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    procurements = invoice.procurements.all().order_by("summary__date")
    response = TemplateResponse(
        request,
        "invoice/invoice_detail.html",
        {"invoice": invoice, "procurements": procurements},
    )
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block="form")
def procurement_create(request):
    if request.method == "POST":
        form = ProcurementCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            account = data["account"]
            item = data["item"]
            price_per_unit = data["price_per_unit"]
            quantity = data["quantity"]
            total = data["total"]
            procured_on = data["procured_on"]

            inventory = get_inventory_account_from_configuration()
            transaction = account.accounting_transfer_to(
                to_account=inventory, amount=total, date=procured_on
            )
            detail = TransactionDetail.objects.create(
                summary=transaction,
                item=item.name,
                quantity=quantity,
                price_per_unit=item.price,
            )
            messages.success(request, _("Procurement created successfully"))
        else:
            messages.error(request, _("Procurement couldn't be created"))
    elif request.htmx and request.method == "GET":
        q = request.GET
        account = q.get("account", None)
        if account:
            account = Account.objects.get(id=account)
        item = q.get("item", None)
        if item:
            item = Item.objects.get(id=item)
        price_per_unit = q.get("price_per_unit", None)
        if item:
            price_per_unit = item.price
        quantity = q.get("quantity", None)
        if item and not quantity:
            quantity = 1
        total = None
        if price_per_unit and quantity:
            total = price_per_unit * quantity
        procured_on = q.get("procured_on", None)
        initial = {
            "account": account,
            "item": item,
            "price_per_unit": price_per_unit,
            "quantity": quantity,
            "total": total,
            "procured_on": procured_on,
        }
        form = ProcurementCreateForm(initial=initial)
    elif request.method == "GET":
        form = ProcurementCreateForm()
    response = TemplateResponse(
        request, "procurement/procurement_create.html", {"form": form}
    )
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def procurement_list(request):
    procurements = Procurement.objects.all()
    return TemplateResponse(
        request, "procurement/procurement_list.html", {"procurements": procurements}
    )


@for_htmx(use_block_from_params=True)
def procurement_detail(request, procurement_id):
    procurement = get_object_or_404(Procurement, id=procurement_id)
    if request.method == "POST":
        form = ProcurementDetailForm(request.POST, instance=procurement)
        if form.is_valid():
            form.save()
            messages.success(request, _("Procurement edited successfully"))
        else:
            messages.error(request, _("Procurement couldn't be edited"))
    else:
        form = ProcurementDetailForm(instance=procurement)
    response = TemplateResponse(
        request, "procurement/procurement_detail.html", {"form": form}
    )
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def company_wise_procurement_ledger(request):
    today = pendulum.today(tz=get_default_timezone())
    vendor = Vendor.objects.first()
    vendor_account = Account.objects.get(name=vendor.name)
    period = vendor.get_invoice_period(today.year, today.month)
    procurements = Leg.objects.filter(account=vendor_account)
    details = TransactionDetail.objects.filter(summary__legs__in=procurements).order_by(
        "summary__date"
    )

    if request.htmx:
        form = CompanyWiseProcurementLedgerFilter(request.GET)
        if form.is_valid():
            vendor = form.cleaned_data["name"]
            period = vendor.get_invoice_period(today.year, today.month)
    else:
        form = CompanyWiseProcurementLedgerFilter()

    return TemplateResponse(
        request,
        "procurement/company_wise_procurement_ledger.html",
        {
            "vendor": vendor,
            "procurements": details,
            "period": period,
            "form": form,
        },
    )


@for_htmx(use_block_from_params=True)
def accounts_payable_ledger(request):
    invoices = Invoice.objects.all()
    return TemplateResponse(
        request, "procurement/accounts_payable_ledger.html", {"invoices": invoices}
    )


@for_htmx(use_block_from_params=True)
def accounts_payable_aging_report(request):
    # This requires both the "due_on" of the Vendor and the Vendor's invoices (to know how past due an invoice is)
    # Account and Transactions to determine if a transfer of funds has been made.

    vendors = Vendor.objects.all()
    return TemplateResponse(
        request,
        "procurement/accounts_payable_aging_report.html",
        {"vendors": vendors},
    )


@for_htmx(use_block_from_params=True)
def business_account_create(request):
    form = AccountForm()
    if request.method == "POST":
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            messages.success(request, f"{account} created successfully")
    response = TemplateResponse(
        request, "accounting/account_create.html", {"form": form}
    )
    return trigger_client_event(response=response, name="getMessages")


# TODO: Make views for Hordak Accounts and Transactions


@for_htmx(use_block_from_params=True)
def business_account_list(request):
    business_accounts = BusinessAccount.objects.all()
    return TemplateResponse(
        request,
        "accounting/account_list.html",
        {"business_accounts": business_accounts},
    )


@for_htmx(use_block_from_params=True)
def business_account_detail(request, business_account_id):
    business_account = get_object_or_404(BusinessAccount, id=business_account_id)
    form = AccountForm(instance=business_account)
    if request.method == "POST":
        form = AccountForm(request.POST, instance=business_account)
        if form.is_valid():
            form.save()
            messages.success(request, f"Account updated successfully")
        else:
            messages.error(request, f"Account couldn't be edited")
    response = TemplateResponse(
        request, "accounting/account_detail.html", {"form": form}
    )
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def business_transaction_create(request):
    form = SimpleTransactionForm()
    if request.method == "POST":
        form = SimpleTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save()
            messages.success(request, f"Transaction successful")
        else:
            messages.error(request, f"Transaction couldn't be completed")
    response = TemplateResponse(
        request, "accounting/business_transaction_create.html", {"form": form}
    )
    return trigger_client_event(response=response, name="getMessages")


@for_htmx(use_block_from_params=True)
def business_transaction_list(request):
    business_transactions = BusinessTransaction.objects.all()
    return TemplateResponse(
        request,
        "accounting/business_transaction_list.html",
        {"business_transactions": business_transactions},
    )


@for_htmx(use_block_from_params=True)
def business_transaction_detail(request, business_transaction_id):
    business_transaction = get_object_or_404(
        BusinessTransaction, id=business_transaction_id
    )
    form = SimpleTransactionForm(instance=business_transaction)
    if request.method == "POST":
        form = SimpleTransactionForm(request.POST, instance=business_transaction)
        if form.is_valid():
            form.save()
            messages.success(request, f"Transaction updated successfully")
        else:
            messages.error(request, f"Transaction couldn't be edited")
    response = TemplateResponse(
        request, "accounting/business_transaction_detail.html", {"form": form}
    )
    return trigger_client_event(response=response, name="getMessages")
