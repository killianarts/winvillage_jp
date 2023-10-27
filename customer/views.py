from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_htmx.http import HttpResponseClientRedirect

import customer.forms as forms
from core.utils import (
    HtmxHttpRequest,
    for_htmx,
)
from customer.models import Customer, make_customers, TicketNote, Ticket


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
                    message=_(
                        f"Customer named { customer.full_name } created successfully!"
                    ),
                )
                return HttpResponseClientRedirect(reverse("winadmin:customer_list"))
            else:
                messages.error(request, message=_("Customer couldn't be created!"))
                context = {"form": form}
    return TemplateResponse(request, "customer/customer_create.html", context)


def customer_create_bulk(request: HtmxHttpRequest) -> HttpResponse:
    customers = make_customers(int(request.POST.get("howmany", "1")))
    if request.method == "POST":
        return HttpResponse(
            "".join(
                format_html("Created {0}<br>", customer.full_name)
                for customer in customers
            )
        )
    return TemplateResponse(request, "customer/customer_create_bulk.html", {})


@for_htmx(use_block_from_params=True)
def customer_list(request: HtmxHttpRequest) -> HttpResponse:
    customers = Customer.objects.all()
    customer_form = forms.CustomerFilterForm()
    context = {}
    if request.htmx:
        first_name = request.GET.get("first_name")
        customer_form = forms.CustomerFilterForm(request.GET)
        if customers.filter(first_name__startswith=str(first_name)).exists():
            customers = customers.filter(first_name__startswith=first_name)
        else:
            customers = Customer.objects.all()
        context = {
            "customers": customers,
            "form": customer_form,
            "GET_first_name": first_name,
        }
        return TemplateResponse(request, "customer/customer_list.html", context)
    context = {"customers": customers, "form": customer_form}
    return TemplateResponse(request, "customer/customer_list.html", context)


def customer_detail(request: HtmxHttpRequest, customer_id: int) -> HttpResponse:
    customer = get_object_or_404(Customer, id=customer_id)

    if request.method == "POST":
        form = forms.CustomerDetailForm(request.POST)

        if form.is_valid():
            if "submit" in request.POST:
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
    return TemplateResponse(request, "customer/customer_detail.html", context)


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
    return TemplateResponse(request, "ticket/ticket_create.html", context)


def ticket_list(request: HtmxHttpRequest) -> HttpResponse:
    tickets = Ticket.objects.all()
    context = {"tickets": tickets}
    return TemplateResponse(request, "ticket/ticket_list.html", context)


def ticket_detail(request: HtmxHttpRequest, ticket_id: int) -> HttpResponse:
    ticket: Ticket = get_object_or_404(Ticket, id=ticket_id)
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
                if "close-ticket" in request.POST:
                    ticket.close_ticket(user=request.user, data=form_data)
                    messages.success(request, _("Note added and ticket closed"))
                    del form_data["notes"]
                    form = forms.TicketReopenForm(initial=form_data)
    else:
        initial = {
            "first_name": ticket.customer.first_name,
            "last_name": ticket.customer.last_name,
            "email": ticket.customer.email,
            "phone": ticket.customer.phone,
        }
        if ticket.is_closed:
            form = forms.TicketReopenForm(initial=initial)
        else:
            form = forms.TicketDetailForm(initial=initial)
    context = {
        "form": form,
        "ticket": ticket,
        "notes": ticket.notes.all().order_by("created_at"),
    }
    return TemplateResponse(request, "ticket/ticket_detail.html", context)
