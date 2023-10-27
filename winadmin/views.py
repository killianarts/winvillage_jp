import uuid
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.timezone import activate, deactivate
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event
from render_block import render_block_to_string
from sendgrid import Mail, SendGridAPIClient
from square.client import Client

from core.models import Item, Category, Transaction, ContactInfo, Customer
from core.utils import (
    HtmxHttpRequest,
    make_get_request,
    get_or_set_reservation_session,
    for_htmx,
    htmx_form_validate,
)
from reservations.models import Reservation, Stay, OrderItem
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
def item_create(request: HtmxHttpRequest) -> HttpResponse:
    return _item_create(request)


@for_htmx(use_block_from_params=True)
def _item_create(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ItemCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, _("Item Successfully Added"))
    form = ItemCreateForm()
    return TemplateResponse(
        request, "winadmin/inventory/item_create.html", {"form": form}
    )


@login_required(login_url="winadmin:login_page")
def category_create(request: HtmxHttpRequest) -> HttpResponse:
    return _category_create(request)


def _category_create(request: HtmxHttpRequest) -> HttpResponse:
    form = CategoryCreateForm()
    context = {"form": form}
    if request.method == "POST":
        form = CategoryCreateForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            category = Category.objects.create(name=name)
            category.save()
            messages.add_message(
                request, messages.INFO, _("Category Successfully Added")
            )
            return _category_create(make_get_request(request))
        elif not form.is_valid():
            if not form.cleaned_data:
                messages.add_message(request, messages.ERROR, _("Input category title"))
                return _category_create(make_get_request(request))
        html = render_block_to_string(
            "winadmin/inventory/category_create.html", "form", context
        )
        return HttpResponse(html)
    return TemplateResponse(request, "winadmin/inventory/category_create.html", context)


@for_htmx(use_block_from_params=True)
def category_edit(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    if request.method == "POST":
        form = CategoryCreateForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            category = get_object_or_404(Category, pk=pk)
            category.title = title
            category.save()
            messages.add_message(
                request, messages.INFO, _("Category Successfully Edited")
            )
            context = {"form": form, "category": category}
            return TemplateResponse(
                request, "winadmin/inventory/category_edit.html", context
            )
        elif not form.is_valid():
            if not form.cleaned_data:
                messages.add_message(request, messages.ERROR, _("Input category title"))
    category = get_object_or_404(Category, pk=pk)
    form = CategoryDetailForm(initial={"title": category.title})
    context = {"form": form, "category": category}
    return TemplateResponse(request, "winadmin/inventory/category_edit.html", context)


def category_list(request: HtmxHttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    context = {
        "categories": categories,
    }
    return TemplateResponse(request, "winadmin/inventory/category_list.html", context)


@login_required(login_url="winadmin:login_page")
@htmx_form_validate(form_class=ItemEditForm)
def item_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    form = ItemEditForm(instance=item)
    if request.method == "POST":
        form = ItemEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, _("Item Successfully Edited"))
            context = {"form": form, "item": item}
            return TemplateResponse(
                request, "winadmin/inventory/item_detail.html", context
            )
        else:
            form = ItemEditForm(request.POST, instance=item)
            messages.error(request, _("Error"))
    return TemplateResponse(
        request, "winadmin/inventory/item_detail.html", {"form": form, "item": item}
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
def transaction_list(request: HtmxHttpRequest) -> HttpResponse:
    return _transaction_list(request)


def _transaction_list(request: HtmxHttpRequest) -> HttpResponse:
    transactions = Transaction.objects.all()
    context = {"transactions": transactions}
    return TemplateResponse(request, "winadmin/transactions/transaction_list", context)


@login_required(login_url="winadmin:login_page")
def sales_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
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
def transaction_create(request: HtmxHttpRequest) -> HttpResponse:
    return _transaction_create(request)


def _transaction_create(request: HtmxHttpRequest) -> HttpResponse:
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
def reservation_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    return _reservation_list_by_period(request)


def _reservation_list_by_period(request: HtmxHttpRequest) -> HttpResponse:
    reservations = (
        Reservation.objects.select_related("stay", "contact_info")
        .exclude(stay__status="not_reserved")
        .order_by("stay__start_datetime")
    )
    form = []
    active_timezone = activate(TIMEZONE)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    deactivate()
    if request.htmx and not request.htmx.boosted:
        form = SetReservationPeriodForm(request.GET)
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    else:
        form = SetReservationPeriodForm(initial={"year": year, "month": month})
        if form.is_valid():
            year = form.cleaned_data["year"]
            month = form.cleaned_data["month"]
    reservations = reservations.filter(stay__start_datetime__year=year).filter(
        stay__start_datetime__month=month
    )
    context = {
        "reservations": reservations,
        "year": year,
        "month": month,
        "form": form,
    }
    if request.htmx and not request.htmx.boosted:
        html = render_block_to_string(
            request=request,
            template_name="winadmin/reservations/reservation_list_by_period",
            block_name="content",
            context=context,
        )
        return HttpResponse(html)
    return TemplateResponse(
        request, "winadmin/reservations/reservation_list_by_period", context
    )


# @login_required(login_url="winadmin:login_page")
# def create_reservation_page(request: HtmxHttpRequest) -> HttpResponse:
#     return _create_reservation_page(request)


def get_grills(reservation) -> tuple[list, QuerySet]:
    reserved_grills_ids = reservation.order_items.filter(
        item__category__title="grill", item__reservation_option=True
    ).values_list("item_id", flat=True)
    unreserved_grills_ids = (
        Item.objects.filter(category__title="grill", reservation_option=True)
        .exclude(id__in=reserved_grills_ids)
        .values_list("id", flat=True)
    )
    all_grills_ids = list(reserved_grills_ids) + list(unreserved_grills_ids)
    all_grills = Item.objects.filter(id__in=all_grills_ids).order_by("pk")
    return reserved_grills_ids, all_grills


@htmx_form_validate(form_class=ReservationCreateForm)
@for_htmx(use_block_from_params=True)
def reservation_create(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    initial = {}
    if reservation.contact_info is not None:
        initial["first_name"] = reservation.contact_info.first_name
        initial["last_name"] = reservation.contact_info.last_name
        initial["email"] = reservation.contact_info.email
    if reservation.stay is not None:
        initial["stay_type"] = reservation.stay.stay_type
        initial["start_datetime"] = reservation.stay.start_datetime
        initial["end_datetime"] = reservation.stay.end_datetime
    reserved_grills_ids, all_grills = get_grills(reservation)
    context = {
        "reservation": reservation,
        "SQUARE_APPLICATION_ID": SQUARE_APPLICATION_ID,
        "SQUARE_LOCATION_ID": SQUARE_LOCATION_ID,
        "SQUARE_CURRENCY": SQUARE_CURRENCY,
        "grills": all_grills,
        "reserved_grill_ids": reserved_grills_ids,
    }
    if request.method == "POST":
        form = ReservationCreateForm(request.POST)
        context["form"] = form
        if form.is_valid():
            stay_type = form.cleaned_data["stay_type"]
            start_datetime = form.cleaned_data["start_datetime"]
            end_datetime = form.cleaned_data["end_datetime"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            if not reservation.stay:
                stay = Stay.objects.create(
                    stay_type=stay_type,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                )
                reservation.stay = stay
                reservation.save()
            else:
                reservation.stay.stay_type = stay_type
                reservation.stay.start_datetime = start_datetime
                reservation.stay.end_datetime = end_datetime
                reservation.stay.save()
                reservation.save()
            if not reservation.contact_info:
                contact_info, created = ContactInfo.objects.get_or_create(
                    first_name=first_name, last_name=last_name, email=email
                )
                if created:
                    contact_info.save()
                reservation.contact_info = contact_info
                reservation.save()
            else:
                reservation.contact_info.first_name = first_name
                reservation.contact_info.last_name = last_name
                reservation.contact_info.email = email
                reservation.save()
        return TemplateResponse(
            request, "winadmin/reservations/reservation_create.html", context
        )
    form = ReservationCreateForm(initial=initial)
    context = {
        "form": form,
        "reservation": reservation,
        "SQUARE_APPLICATION_ID": SQUARE_APPLICATION_ID,
        "SQUARE_LOCATION_ID": SQUARE_LOCATION_ID,
        "SQUARE_CURRENCY": SQUARE_CURRENCY,
        "grills": all_grills,
        "reserved_grill_ids": reserved_grills_ids,
    }
    return TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )


# @for_htmx(use_block_from_params=True)
# def create_reservation_page(request: HtmxHttpRequest) -> HttpResponse:
#     return TemplateResponse(request, template_path, context)
#
#
# @htmx_form_validate(form_class=StayForm)
# @for_htmx(use_block_from_params=True)
# def _stay_form(request: HtmxHttpRequest) -> HttpResponse:
#     if request.method == "POST":
#         if "create" in request:
#             pass
#     return TemplateResponse(request, template_path, context)
#
#
# @htmx_form_validate(form_class=ContactInfoForm)
# @for_htmx(use_block_from_params=True)
# def _contact_info_form(request: HtmxHttpRequest) -> HttpResponse:
#     return TemplateResponse(request, template_path, context)
#
#
# @for_htmx(use_block_from_params=True)
# def _options(request: HtmxHttpRequest) -> HttpResponse:
#     return TemplateResponse(request, template_path, context)
#
#
# @for_htmx(use_block_from_params=True)
# def _payment_form(request: HtmxHttpRequest) -> HttpResponse:
#     return TemplateResponse(request, template_path, context)


@require_POST
@for_htmx(use_block_from_params=True)
def add_grill_reservation_option(request: HtmxHttpRequest, pk) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    if reservation:
        order_item, created = OrderItem.objects.get_or_create(
            user=request.user, item_id=pk
        )
        order_item.save()
        reservation.order_items.add(order_item)
        reservation.save()
    reserved_grill_ids, all_grills = get_grills(reservation)
    context = {"reserved_grill_ids": reserved_grill_ids, "grills": all_grills}
    response = TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )
    return trigger_client_event(response, "updatePrice")


@require_POST
@for_htmx(use_block_from_params=True)
def remove_grill_reservation_option(request: HtmxHttpRequest, pk) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    reservation.order_items.filter(user=request.user, item_id=pk).first().delete()
    reserved_grill_ids, all_grills = get_grills(reservation)
    context = {"reserved_grill_ids": reserved_grill_ids, "grills": all_grills}
    response = TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )
    return trigger_client_event(response, "updatePrice")


@for_htmx(use_block_from_params=True)
def update_price(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    context = {"reservation": reservation}
    return TemplateResponse(
        request, "winadmin/reservations/reservation_create.html", context
    )


@login_required(login_url="winadmin:login_page")
def reservation_detail(request: HtmxHttpRequest, pk) -> HttpResponse:
    return _reservation_detail(request, pk)


def _reservation_detail(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    reservation = get_object_or_404(Reservation, pk=pk)
    stay_type = reservation.stay.stay_type
    start_datetime = reservation.stay.start_datetime
    end_datetime = reservation.stay.end_datetime
    first_name = reservation.contact_info.first_name
    last_name = reservation.contact_info.last_name
    email = reservation.contact_info.email
    options = reservation.order_items
    initial = {
        "stay_type": stay_type,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "options": options,
    }
    form = ReservationDetailForm(initial=initial)
    if request.method == "POST":
        if form.is_valid():
            stay_type = form.cleaned_data["stay_type"]
            start_datetime = form.cleaned_data["start_datetime"]
            end_datetime = form.cleaned_data["end_datetime"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            email = form.cleaned_data["email"]
            options = form.cleaned_data["options"]
            reservation.stay.stay_type = stay_type
            reservation.stay.start_datetime = start_datetime
            reservation.stay.end_datetime = end_datetime
            reservation.stay.save()
            contact_info, created = ContactInfo.objects.get_or_create(
                first_name=first_name, last_name=last_name, email=email
            )
            reservation.contact_info.first_name = first_name
            reservation.contact_info.last_name = last_name
            reservation.contact_info.email = email
            reservation.contact_info.save()
            for option_id in options:
                order_item, created = OrderItem.objects.get_or_create(item_id=option_id)
                order_item.save()
                reservation.order_items.add(order_item)
            reservation.stay.status = Stay.STATUS.reserved
            reservation.save()
            messages.add_message(
                request, messages.INFO, _("Reservation successfully edited.")
            )
            return reservation_detail(make_get_request(request), pk)
    return TemplateResponse(
        request,
        "winadmin/reservations/reservation_detail.html",
        {"form": form, "reservation": reservation},
    )


def get_client():
    client = Client(access_token=SQUARE_ACCESS_TOKEN, environment=SQUARE_ENVIRONMENT)
    return client


def get_or_create_customer(reservation):
    customer, created = Customer.objects.get_or_create(
        contact_info=reservation.contact_info
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


def send_confirmation_email(reservation):
    message = Mail(
        from_email="noreply@winvillage.jp",
        to_emails=reservation.contact_info.email,
        subject=f"{_('Winvillage Reservation Confirmation For')}, {reservation.contact_info.first_name}",
        html_content="This is some placeholder text",
    )
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
