import calendar as stdlib_calendar
import json
import locale
from datetime import datetime
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from render_block import render_block_to_string
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from square.client import Client
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from core.utils import HtmxHttpRequest, make_get_request
from core.models import Item, Category, Transaction
from winadmin.forms import (
    LoginForm,
    CreateItemForm,
    CreateCategoryForm,
    EditItemForm,
    CreateTransactionForm,
    SetLedgerPeriodForm,
)

# Index and Login


@login_required()
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


def _edit_inventory_item(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = get_object_or_404(Item, pk=pk)
    form = EditItemForm(instance=item)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, _("Item Successfully Edited"))
            return edit_inventory_item(make_get_request(request), pk)
    return TemplateResponse(
        request, "winadmin/inventory/edit_item.html", {"form": form, "item": item}
    )


@login_required(login_url="winadmin:login_page")
def delete_inventory_item(request: HtmxHttpRequest) -> HttpResponse:
    pass


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
    year = request.GET.get("year", datetime.now().year)
    month = request.GET.get("month", datetime.now().month)
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
                request, "winadmin/transactions/create_transaction.html", context
            )
    form = CreateTransactionForm()
    context = {"form": form}
    return TemplateResponse(
        request, "winadmin/transactions/create_transaction.html", context
    )


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
                request, "winadmin/transactions/create_transaction.html", context
            )
    form = CreateTransactionForm()
    context = {"form": form}
    return TemplateResponse(
        request, "winadmin/transactions/create_transaction.html", context
    )
