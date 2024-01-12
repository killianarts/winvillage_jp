from datetime import datetime

from django import forms
from django.forms.renderers import TemplatesSetting
from django.utils.translation import gettext_lazy as _
from model_utils import Choices

from core.forms import TailwindFormMixin
from core.models import Item, Category, Transaction
from reservations.models import Stay, ContactInfo


class LoginForm(TailwindFormMixin, forms.Form):
    username = forms.CharField(label=_("Username"), max_length=30)
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, max_length=30
    )


class ItemCreateFormRenderer(TemplatesSetting):
    form_template_name = "winadmin/forms/item_create/div.html"
    single_field_row_template = "winadmin/forms/item_create/field_row.html"


class ItemCreateFormMixin:
    default_renderer = ItemCreateFormRenderer()
    do_htmx_validation = False

    # def __init__(self, *args, **kwargs) -> None:
    # We don’t want ':' as a label suffix:
    # return super().__init__(*args, label_suffix="", **kwargs)

    def get_context(self, *args, **kwargs):
        return super().get_context(*args, **kwargs) | {
            "do_htmx_validation": self.do_htmx_validation,
            "single_field_row_template": self.renderer.single_field_row_template,
        }


class ItemCreateForm(ItemCreateFormMixin, forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "price",
            "category",
            "image",
            "stock_quantity",
            "in_stock",
            "active",
            "reservation_option",
            "description",
            "short_description",
        ]


class ItemEditForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "price",
            "category",
            "image",
            "stock_quantity",
            "in_stock",
            "active",
            "reservation_option",
            "description",
            "short_description",
        ]

    do_htmx_validation = True


class CategoryCreateForm(TailwindFormMixin, forms.Form):
    name = forms.CharField(label=_("Category Name"))
    do_htmx_validation = False


class CategoryDetailForm(TailwindFormMixin, forms.Form):
    name = forms.CharField(label=_("Category Name"))
    do_htmx_validation = False


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class DateTimeInput(forms.DateTimeInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class TransactionCreateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            "name",
            "customer",
            "transaction_datetime",
            "item",
            "quantity",
            "total_price",
        ]
        widgets = {"transaction_datetime": DateInput()}


class SetLedgerPeriodForm(forms.Form):
    current_year = datetime.today().year
    current_month = datetime.today().month
    year = forms.IntegerField(max_value=current_year)
    month = forms.IntegerField(max_value=current_month)


class SetReservationPeriodForm(forms.Form):
    year = forms.IntegerField()
    month = forms.IntegerField()


class ReservationCreateForm(TailwindFormMixin, forms.Form):
    STAY_TYPE_CHOICES = Choices(("hourly", _("Hourly")), ("overnight", _("Overnight")))
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    stay_type = forms.ChoiceField(choices=STAY_TYPE_CHOICES, label=_("Stay Type"))
    start = forms.DateTimeField(widget=DateInput, label=_("Start Date"))
    end = forms.DateTimeField(widget=DateInput, label=_("End Date"))

    do_htmx_validation = True


class StayForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Stay
        fields = [
            "stay_type",
            "start",
            "end",
        ]
        widgets = {"start": DateInput(), "end": DateInput()}

    do_htmx_validation = True


class ContactInfoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ["first_name", "last_name", "email"]

    do_htmx_validation = True


class ReservationDetailForm(TailwindFormMixin, forms.Form):
    STAY_TYPE_CHOICES = Choices(("hourly", _("Hourly")), ("overnight", _("Overnight")))
    STATUS_CHOICES = Choices(
        ("not_reserved", _("Not Reserved")),
        ("reserved", _("Reserved")),
        ("checked_in", _("Checked In")),
        ("checked_out", _("Checked Out")),
        ("cancelled", _("Cancelled")),
    )
    status = forms.ChoiceField(choices=STATUS_CHOICES)
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    start = forms.DateTimeField(widget=DateInput, label=_("Start"))
    end = forms.DateTimeField(widget=DateInput, label=_("End"))
    stay_type = forms.ChoiceField(choices=STAY_TYPE_CHOICES, label=_("Stay Type"))


class SquarePaymentTokenForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())
