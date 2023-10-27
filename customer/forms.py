from django import forms
from django.forms.renderers import TemplatesSetting
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from core.forms import TailwindFormMixin


class CustomerDetailForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.CharField(label=_("Email"))
    phone = forms.CharField(label=_("Phone #"))

    do_htmx_validation = False


class CustomerCreateForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.CharField(label=_("Email"))
    phone = forms.CharField(label=_("Phone #"))

    do_htmx_validation = False


class CustomerFilterForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.CharField(label=_("Email"))
    phone = forms.CharField(label=_("Phone #"))

    do_htmx_validation = False


class TicketFormRenderer(TemplatesSetting):
    form_template_name = "ticket/forms/tailwind/div.html"
    single_field_row_template = "ticket/forms/tailwind/field_row.html"


class TicketFormMixin:
    default_renderer = TicketFormRenderer()

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {
            "single_field_row_template": self.renderer.single_field_row_template,
        }


class TicketCreateForm(TicketFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))
    notes = forms.CharField(label=_("Notes"), widget=forms.Textarea)

    do_htmx_validation = False


class TicketDetailForm(TicketFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))
    notes = forms.CharField(label=_("Notes"), widget=forms.Textarea)

    do_htmx_validation = False


class TicketReopenForm(TicketFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))

    do_htmx_validation = False
