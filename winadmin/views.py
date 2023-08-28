import calendar as stdlib_calendar
import json
import locale
from datetime import datetime

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
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
from core.models import Item, Category
from winadmin.forms import LoginForm, CreateItemForm, CreateCategoryForm

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


def view_inventory_item(request: HtmxHttpRequest, pk: int) -> HttpResponse:
    item = Item.objects.get_or_404(pk=pk)
    return HttpResponse(item)


@login_required(login_url="winadmin:login_page")
def create_inventory_item_page(request: HtmxHttpRequest) -> HttpResponse:
    return _create_inventory_item_page(request)


def _create_inventory_item_page(request: HtmxHttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CreateItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, "Item Successfully Added")
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
            messages.add_message(request, messages.INFO, "Category Successfully Added")
            return _create_category_page(make_get_request(request))
        elif not form.is_valid():
            if not form.cleaned_data:
                messages.add_message(request, messages.ERROR, "Input category title")
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
def view_inventory_item(request: HtmxHttpRequest) -> HttpResponse:
    pass


@login_required(login_url="winadmin:login_page")
def update_inventory_item(request: HtmxHttpRequest) -> HttpResponse:
    pass


@login_required(login_url="winadmin:login_page")
def delete_inventory_item(request: HtmxHttpRequest) -> HttpResponse:
    pass
