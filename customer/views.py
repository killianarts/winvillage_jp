from django.contrib import messages
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory, formset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_htmx.http import HttpResponseClientRedirect, trigger_client_event

import customer.forms as forms
from core.models import Item, Transaction
from core.utils import (
    HtmxHttpRequest,
    for_htmx,
    htmx_form_validate,
)
from customer.models import Customer, make_customers, TicketNote, Ticket
from reservations.models import Reservation, Room, Order, OrderItem


@login_required(login_url="winadmin:login_page")
def customer_create(request: HtmxHttpRequest) -> HttpResponse:
    form = forms.CustomerCreateForm()
    context = {"form": form}
    if request.method == "POST":
        if "submit" in request.POST:
            form = forms.CustomerCreateForm(request.POST)
            if form.is_valid():
                customer = form.save()
                messages.success(
                    request,
                    message=_("Customer named %(customer_full_name)s created successfully!")
                    % {"customer_full_name": customer.full_name},
                )
                return HttpResponseClientRedirect(reverse("winadmin:customer_list"))
            else:
                messages.error(request, message=_("Customer couldn't be created!"))
                context = {"form": form}
    return trigger_client_event(
        TemplateResponse(request, "customer/customer_create.html", context),
        "getMessages",
    )


@login_required(login_url="winadmin:login_page")
def customer_create_bulk(request: HtmxHttpRequest) -> HttpResponse:
    customers = make_customers(int(request.POST.get("howmany", "1")))
    if request.method == "POST":
        return HttpResponse("".join(format_html("Created {0}<br>", customer.full_name) for customer in customers))
    return TemplateResponse(request, "customer/customer_create_bulk.html", {})


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def customer_list(request: HtmxHttpRequest) -> HttpResponse:
    customers = Customer.objects.all()
    customer_form = forms.CustomerFilterForm()
    first_name = request.GET.get("first_name", False)
    if request.htmx:
        customer_form = forms.CustomerFilterForm(request.GET)
        if customers.filter(first_name__startswith=str(first_name)).exists():
            customers = customers.filter(first_name__startswith=first_name)
        else:
            customers = Customer.objects.all()
    context = {"customers": customers, "form": customer_form, "first_name": first_name}
    return TemplateResponse(request, "customer/customer_list.html", context)


@htmx_form_validate(form_class=forms.CustomerDetailForm)
@for_htmx(use_block_from_params=True)
@login_required(login_url="winadmin:login_page")
def customer_detail(request: HtmxHttpRequest, customer_id: int) -> HttpResponse:
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        form = forms.CustomerDetailForm(request.POST)

        if "submit" in request.POST:
            if form.is_valid():
                for field in ["first_name", "last_name", "email", "phone"]:
                    setattr(customer, field, form.cleaned_data[field])
                customer.save()
                messages.success(request, _("Customer edited successfully!"))

        if "delete" in request.POST:
            customer.delete()
            messages.success(request, _("Customer deleted successfully!"))
            return HttpResponseClientRedirect(reverse("winadmin:customer_list"))

        else:
            messages.error(request, _("Customer couldn't be edited!"))

    else:
        initial = {
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "email": customer.email,
            "phone": customer.phone,
        }
        form = forms.CustomerDetailForm(initial=initial)

    context = {"form": form, "customer": customer}
    return trigger_client_event(
        TemplateResponse(
            request,
            "customer/customer_detail.html",
            context,
        ),
        "getMessages",
    )


@login_required(login_url="winadmin:login_page")
def ticket_create(request: HtmxHttpRequest) -> HttpResponse:
    form = forms.TicketCreateForm()
    context = {"form": form}
    if request.method == "POST":
        if "submit" in request.POST:
            form = forms.TicketCreateForm(request.POST)
            if form.is_valid():
                first_name = form.cleaned_data["first_name"]
                last_name = form.cleaned_data["last_name"]
                email = form.cleaned_data["email"]
                phone = form.cleaned_data["phone"]
                notes = form.cleaned_data["notes"]
                customer, create = Customer.objects.get_or_create(
                    first_name=first_name, last_name=last_name, email=email, phone=phone
                )
                customer.save()
                note = TicketNote.objects.create(user=request.user, text=notes)
                note.save()
                ticket = Ticket.objects.create(customer=customer)
                ticket.save()
                ticket.notes.add(note)
                ticket.save()
                messages.success(
                    request,
                    message=_(f"Ticket created successfully!"),
                )
                return HttpResponseClientRedirect(reverse("winadmin:ticket_list"))
            else:
                messages.error(request, message=_("Ticket couldn't be created!"))
                context = {"form": form}
    return trigger_client_event(TemplateResponse(request, "ticket/ticket_create.html", context), "getMessages")


@login_required(login_url="winadmin:login_page")
def ticket_list(request: HtmxHttpRequest) -> HttpResponse:
    tickets = Ticket.objects.all()
    context = {"tickets": tickets}
    return TemplateResponse(request, "ticket/ticket_list.html", context)


@login_required(login_url="winadmin:login_page")
@for_htmx(use_block_from_params=True)
def ticket_detail(request: HtmxHttpRequest, ticket_id: int) -> HttpResponse:
    ticket: Ticket = get_object_or_404(Ticket, id=ticket_id)
    initial = {
        "first_name": ticket.customer.first_name,
        "last_name": ticket.customer.last_name,
        "email": ticket.customer.email,
        "phone": ticket.customer.phone,
    }
    if request.method == "POST":
        if ticket.is_closed:
            form = forms.TicketReopenForm(request.POST)
            if form.is_valid():
                form_data = {
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                    "email": form.cleaned_data["email"],
                    "phone": form.cleaned_data["phone"],
                    "notes": _("Ticket reopened."),
                }
                ticket.reopen_ticket(user=request.user, data=form_data)
                messages.success(request, _("Ticket reopened"))
                del form_data["notes"]
                form = forms.TicketDetailForm(initial=form_data)
        else:
            form = forms.TicketDetailForm(request.POST)
            if form.is_valid():
                form_data = {
                    "first_name": form.cleaned_data["first_name"],
                    "last_name": form.cleaned_data["last_name"],
                    "email": form.cleaned_data["email"],
                    "phone": form.cleaned_data["phone"],
                    "notes": form.cleaned_data["notes"],
                }
                if "add-note" in request.POST:
                    ticket.add_note(user=request.user, data=form_data)
                    messages.success(request, _("Note added to ticket."))
                    form = forms.TicketDetailForm(initial=initial)
                if "close-ticket" in request.POST:
                    ticket.close_ticket(user=request.user, data=form_data)
                    messages.success(request, _("Note added and ticket closed"))
                    del form_data["notes"]
                    form = forms.TicketReopenForm(initial=form_data)
    else:
        if ticket.is_closed:
            form = forms.TicketReopenForm(initial=initial)
        else:
            form = forms.TicketDetailForm(initial=initial)
    context = {
        "form": form,
        "ticket": ticket,
        "notes": ticket.notes.all().order_by("created_at"),
    }
    return trigger_client_event(TemplateResponse(request, "ticket/ticket_detail.html", context), "getMessages")


def occupied_room_list(request):
    rooms = Room.objects.all()
    occupied_rooms = Room.objects.occupied_rooms()
    reservations = Reservation.objects.filter(stay__room__in=occupied_rooms)
    rooms_with_occupants = {}
    form = None
    for room in rooms:
        customer = None
        if room in occupied_rooms:
            if reservations.filter(stay__status="checked_in").exists():
                customer = reservations.get(stay__room=room, stay__status="checked_in").customer
        rooms_with_occupants[room] = customer

    context = {
        "form": form,
        "reservations": reservations,
        "rooms": rooms,
        "occupied_rooms": occupied_rooms,
        "rooms_with_occupants": rooms_with_occupants,
    }
    return TemplateResponse(request, "customer/occupied_room_list.html", context)


@for_htmx(use_block_from_params=True)
def checked_in_customer_purchase(request, room_id, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    customer_information_form = forms.CustomerForm(instance=customer)
    order, created = Order.objects.get_or_create(customer=customer, ordered=False)
    room = Room.objects.get(id=room_id)
    shop_items = Item.in_stock.with_orderitem_quantities(order).order_by("category", "name")
    shop_item_forms = []
    for item in shop_items:
        initial = {"item_id": item.id, "name": item.name, "price": item.price, "quantity": item.quantity_in_order}
        form = forms.ItemForm(initial=initial)
        shop_item_forms.append([item, form])
    if request.method == "POST":
        form = forms.ItemForm(request.POST)
        if request.htmx:
            if form.is_valid():
                item_id = form.cleaned_data["item_id"]
                quantity = form.cleaned_data["quantity"]
                order_item, created = OrderItem.objects.get_or_create(item_id=item_id)
                if created:
                    order.items.add(order_item)
                    order.save()
                if quantity > 0:
                    order_item.quantity = quantity
                    order_item.save()
                else:
                    order_item.delete()
        if "check-out" in request.POST:
            transactions = Transaction.sales.create_sales_from_order(order_obj=order)
            for orderitem in order.items.all():
                orderitem.item.stock_quantity -= orderitem.quantity
                orderitem.item.save()
            order.ordered = True
            order.save()
            messages.success(request, _("Purchase Completed."))
            return HttpResponseClientRedirect(reverse("winadmin:index"))
        elif "cancel" in request.POST:
            if order:
                order.delete()
                messages.success(request, _("Purchase Cancelled."))
                return HttpResponseClientRedirect(reverse("winadmin:index"))

    context = {
        "customer_information_form": customer_information_form,
        "customer": customer,
        "order": order,
        "order_items": order.items.all(),
        "shop_item_forms": shop_item_forms,
        "room": room,
    }
    response = TemplateResponse(request, "customer/checked_in_customer_purchase.html", context)
    return trigger_client_event(response, "getMessages")


@for_htmx(use_block_from_params=True)
def checked_in_customer_return(request, room_id, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    customer_information_form = forms.CustomerForm(instance=customer)
    order, created = Order.objects.get_or_create(customer=customer, ordered=False)
    room = Room.objects.get(id=room_id)
    shop_items = Item.in_stock.with_orderitem_quantities(order).order_by("category", "name")
    shop_item_forms = []
    for item in shop_items:
        initial = {"item_id": item.id, "name": item.name, "price": item.price, "quantity": item.quantity_in_order}
        form = forms.ItemForm(initial=initial)
        shop_item_forms.append([item, form])
    if request.method == "POST":
        form = forms.ItemForm(request.POST)
        if request.htmx:
            if form.is_valid():
                item_id = form.cleaned_data["item_id"]
                quantity = form.cleaned_data["quantity"]
                order_item, created = OrderItem.objects.get_or_create(item_id=item_id)
                if created:
                    order.items.add(order_item)
                    order.save()
                if quantity > 0:
                    order_item.quantity = quantity
                    order_item.save()
                else:
                    order_item.delete()
        if "check-out" in request.POST:
            transactions = Transaction.returns.create_returns_from_order(order_obj=order)
            for orderitem in order.items.all():
                orderitem.item.stock_quantity += orderitem.quantity
                orderitem.item.save()
            order.ordered = True
            order.save()
            messages.success(request, _("Return Completed."))
            return HttpResponseClientRedirect(reverse("winadmin:index"))
        elif "cancel" in request.POST:
            if order:
                order.delete()
                messages.success(request, _("Return Cancelled."))
                return HttpResponseClientRedirect(reverse("winadmin:index"))

    context = {
        "customer_information_form": customer_information_form,
        "customer": customer,
        "order": order,
        "order_items": order.items.all(),
        "shop_item_forms": shop_item_forms,
        "room": room,
    }
    response = TemplateResponse(request, "customer/checked_in_customer_return.html", context)
    return trigger_client_event(response, "getMessages")
