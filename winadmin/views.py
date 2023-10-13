import uuid
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.timezone import activate, deactivate
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_htmx.http import trigger_client_event
from render_block import render_block_to_string
from square.client import Client

from core.models import Item, Category, Transaction, ContactInfo
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
    CreateItemForm,
    CreateCategoryForm,
    EditItemForm,
    CreateTransactionForm,
    SetLedgerPeriodForm,
    SetReservationPeriodForm,
    CreateReservationForm,
    EditReservationForm,
    SquarePaymentTokenForm,
)
from winvillage.settings import SQUARE_SETTINGS

SQUARE_APPLICATION_ID = SQUARE_SETTINGS["SQUARE_APPLICATION_ID"]
SQUARE_LOCATION_ID = SQUARE_SETTINGS["SQUARE_LOCATION_ID"]
SQUARE_CURRENCY = SQUARE_SETTINGS["SQUARE_CURRENCY"]
SQUARE_ACCESS_TOKEN = SQUARE_SETTINGS["SQUARE_ACCESS_TOKEN"]
SQUARE_ENVIRONMENT = SQUARE_SETTINGS["SQUARE_ENVIRONMENT"]

TIMEZONE = "Asia/Tokyo"


# Index and Login
@login_required(login_url="winadmin:login_page")
def index(request: HtmxHttpRequest) -> HttpResponse:
    return TemplateResponse(request, "winadmin/index.html", {})


def login_page(request: HtmxHttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        # return index(make_get_request(request))
        return redirect("winadmin:index")
    form = LoginForm()
    context = {"form": form}
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # return index(make_get_request(request))
                return redirect("winadmin:index")

    return TemplateResponse(request, "winadmin/login_page.html", context)


@login_required(login_url="winadmin:login_page")
def _logout(request: HtmxHttpRequest) -> HttpResponse:
    logout(request)
    return redirect("winadmin:login_page")


# Inventory


@login_required(login_url="winadmin:login_page")
def list_inventory(request: HtmxHttpRequest) -> HttpResponse:
    items = Item.objects.all()
    context = {"items": items}
    return TemplateResponse(request, "winadmin/inventory/index.html", context)


@login_required(login_url="winadmin:login_page")
def create_inventory_item_page(request: HtmxHttpRequest) -> HttpResponse:
    return _create_inventory_item_page(request)


def _create_inventory_item_page(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CreateItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, _("Item Successfully Added"))
            return _create_inventory_item_page(make_get_request(request))
        html = render_block_to_string(
            "winadmin/inventory/create_item.html", "content", {"form": form}
        )
        return HttpResponse(html)
    form = CreateItemForm()
    return TemplateResponse(
        request, "winadmin/inventory/create_item.html", {"form": form}
    )


@login_required(login_url="winadmin:login_page")
def create_category_page(request: HtmxHttpRequest) -> HttpResponse:
    return _create_category_page(request)


def _create_category_page(request: HtmxHttpRequest) -> HttpResponse:
    form = CreateCategoryForm()
    context = {"form": form}
    if request.method == "POST":
        form = CreateCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.INFO, _("Category Successfully Added")
            )
            return _create_category_page(make_get_request(request))
        elif not form.is_valid():
            if not form.cleaned_data:
                messages.add_message(request, messages.ERROR, _("Input category title"))
                return _create_category_page(make_get_request(request))
        html = render_block_to_string(
            "winadmin/inventory/create_category.html", "form", context
        )
        return HttpResponse(html)
    return TemplateResponse(request, "winadmin/inventory/create_category.html", context)


def list_categories_page(request: HtmxHttpRequest) -> HttpResponse:
    categories = Category.objects.all()
    context = {
        "categories": categories,
    }
    return TemplateResponse(request, "winadmin/inventory/list_categories.html", context)


@login_required(login_url="winadmin:login_page")
def edit_inventory_item(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    return _edit_inventory_item(request, pk)


@htmx_form_validate(form_class=EditItemForm)
def edit_inventory_item(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    form = EditItemForm(instance=item)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, _("Item Successfully Edited"))
            # return edit_inventory_item(make_get_request(request), pk)
        else:
            messages.error(request, _("Error"))
    return TemplateResponse(
        request, "winadmin/inventory/edit_item.html", {"form": form, "item": item}
    )


@login_required(login_url="winadmin:login_page")
def delete_inventory_item(request: HtmxHttpRequest) -> HttpResponse:
    pass


# Transactions
@login_required(login_url="winadmin:login_page")
def view_all_transactions(request: HtmxHttpRequest) -> HttpResponse:
    return _view_all_transactions(request)


def _view_all_transactions(request: HtmxHttpRequest) -> HttpResponse:
    transactions = Transaction.objects.all()
    context = {"transactions": transactions}
    return TemplateResponse(
        request, "winadmin/transactions/list_transactions.html", context
    )


@login_required(login_url="winadmin:login_page")
def view_sales_by_period(request: HtmxHttpRequest) -> HttpResponse:
    return _view_sales_by_period(request)


def _view_sales_by_period(request: HtmxHttpRequest) -> HttpResponse:
    sales = Transaction.objects.filter(
        name__in=["sale", "payment", "deposit", "return"]
    ).order_by("transaction_datetime")
    form = []
    active_timezone = activate(TIMEZONE)
    year = request.GET.get("year", datetime.now(tz=active_timezone).year)
    month = request.GET.get("month", datetime.now(tz=active_timezone).month)
    deactivate()
    if request.htmx and not request.htmx.boosted:
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
    balance = 0
    ledger = []
    for sale in sales:
        if sale.name == "sale":
            balance += sale.total_price_rounded
        elif sale.name == "return":
            balance -= sale.total_price_rounded
        ledger.append([sale, balance])
    context = {
        "ledger": ledger,
        "final_balance": balance,
        "year": year,
        "month": month,
        "form": form,
    }
    if request.htmx and not request.htmx.boosted:
        html = render_block_to_string(
            request=request,
            template_name="winadmin/transactions/list_sales_by_period.html",
            block_name="content",
            context=context,
        )
        return HttpResponse(html)
    return TemplateResponse(
        request, "winadmin/transactions/list_sales_by_period.html", context
    )


@login_required(login_url="winadmin:login_page")
def create_transaction(request: HtmxHttpRequest) -> HttpResponse:
    return _create_transaction(request)


def _create_transaction(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CreateTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.INFO, _("Transaction Created Successfully")
            )
            return _create_transaction(make_get_request(request))
        elif not form.is_valid():
            return TemplateResponse(
                request, "winadmin/transactions/create_transaction.html", {}
            )
    form = CreateTransactionForm()
    context = {"form": form}
    return TemplateResponse(
        request, "winadmin/transactions/create_transaction.html", context
    )


@login_required(login_url="winadmin:login_page")
def edit_transaction(request: HtmxHttpRequest) -> HttpResponse:
    return _create_transaction(request)


def _edit_transaction(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CreateTransactionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                request, messages.INFO, _("Transaction Created Successfully")
            )
            return _create_transaction(make_get_request(request))
        elif not form.is_valid():
            return TemplateResponse(
                request, "winadmin/transactions/create_transaction.html", {}
            )
    form = CreateTransactionForm()
    context = {"form": form}
    return TemplateResponse(
        request, "winadmin/transactions/create_transaction.html", context
    )


# Reservations


@login_required(login_url="winadmin:login_page")
def view_reservations_by_period(request: HtmxHttpRequest) -> HttpResponse:
    return _view_reservations_by_period(request)


def _view_reservations_by_period(request: HtmxHttpRequest) -> HttpResponse:
    reservations = Reservation.objects.select_related("stay", "contact_info").order_by(
        "stay__start_datetime"
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
            template_name="winadmin/transactions/list_reservations_by_period.html",
            block_name="content",
            context=context,
        )
        return HttpResponse(html)
    return TemplateResponse(
        request, "winadmin/transactions/list_reservations_by_period.html", context
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


@htmx_form_validate(form_class=CreateReservationForm)
@for_htmx(use_block_from_params=True)
def create_reservation_page(request: HtmxHttpRequest) -> HttpResponse:
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
        form = CreateReservationForm(request.POST)
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
            request, "winadmin/reservations/create_reservation.html", context
        )
    form = CreateReservationForm(initial=initial)
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
        request, "winadmin/reservations/create_reservation.html", context
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
        request, "winadmin/reservations/create_reservation.html", context
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
        request, "winadmin/reservations/create_reservation.html", context
    )
    return trigger_client_event(response, "updatePrice")


@for_htmx(use_block_from_params=True)
def update_price(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    context = {"reservation": reservation}
    return TemplateResponse(
        request, "winadmin/reservations/create_reservation.html", context
    )


@login_required(login_url="winadmin:login_page")
def edit_reservation(request: HtmxHttpRequest, pk) -> HttpResponse:
    return _edit_reservation(request, pk)


def _edit_reservation(request: HtmxHttpRequest, pk: int) -> HttpResponse:
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
    form = EditReservationForm(initial=initial)
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
            return edit_reservation(make_get_request(request), pk)
    return TemplateResponse(
        request,
        "winadmin/reservations/edit_reservation.html",
        {"form": form, "reservation": reservation},
    )


def get_client():
    client = Client(access_token=SQUARE_ACCESS_TOKEN, environment=SQUARE_ENVIRONMENT)
    return client


@for_htmx(use_block_from_params=True)
def make_payment(request: HtmxHttpRequest) -> HttpResponse:
    reservation = get_or_set_reservation_session(request)
    context = None
    """This function just gets the token from the Square SDK and then handles the rest."""
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
        context = {"payment": payment}
        return TemplateResponse(
            request, "winadmin/reservations/create_reservation.html", context
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
        request, "winadmin/reservations/create_reservation.html", context
    )


def send_confirmation_email(request):
    subscription_id = "r2rRb32AP4gWx0JRBxdiPw"

    body = {"event_type": "payment.created"}
    client = get_client()
    webhook_subscriptions_api = client.webhook_subscriptions
    result = webhook_subscriptions_api.test_webhook_subscription(subscription_id, body)
    print(result)

    if result.is_success():
        return JsonResponse(result.body, safe=False)
    elif result.is_error():
        return JsonResponse(result.errors, safe=False)
