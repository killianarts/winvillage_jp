from datetime import datetime

import pendulum
from core.forms import PendulumField, TailwindFormMixin
from core.models import Invoice, Item, Procurement, TransactionDetail, Vendor
from django import forms
from django.forms import BaseInlineFormSet, widgets
from django.forms.renderers import TemplatesSetting
from django.utils.translation import gettext_lazy as _
from djmoney.forms import MoneyField
from hordak.forms import accounts as account_forms
from hordak.forms import transactions as transaction_forms
from hordak.models import CURRENCY_CHOICES, Account
from model_utils import Choices
from mptt.forms import TreeNodeChoiceField
from phonenumber_field.formfields import PhoneNumberField
from reservations.models import (
    Campaign,
    ContactInfo,
    PricingTier,
    PricingTierGroup,
    Room,
    RoomTier,
    Stay,
)


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
            "active",
            "reservation_option",
            "description",
            "short_description",
        ]
        labels = {
            "name": _("Name"),
            "price": _("Price"),
            "category": _("Category"),
            "image": _("Image"),
            "stock_quantity": _("Stock Quantity"),
            "active": _("Active"),
            "reservation_option": _("Reservation Option"),
            "description": _("Description"),
            "short_description": _("Short Description"),
        }


class ItemEditForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "price",
            "category",
            "image",
            "stock_quantity",
            "active",
            "reservation_option",
            "description",
            "short_description",
        ]
        labels = {
            "name": _("Name"),
            "price": _("Price"),
            "category": _("Category"),
            "image": _("Image"),
            "stock_quantity": _("Stock Quantity"),
            "active": _("Active"),
            "reservation_option": _("Reservation Option"),
            "description": _("Description"),
            "short_description": _("Short Description"),
        }

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


class SetLedgerPeriodForm(forms.Form):
    current_year = datetime.today().year
    current_month = datetime.today().month
    year = forms.IntegerField(max_value=current_year)
    month = forms.IntegerField(max_value=current_month)


class SetReservationPeriodForm(forms.Form):
    year = forms.IntegerField()
    month = forms.IntegerField()
    day = forms.IntegerField()


class ReservationCreateForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    start = forms.DateTimeField(widget=DateInput, label=_("Start Date"))
    end = forms.DateTimeField(widget=DateInput, label=_("End Date"))

    do_htmx_validation = True


class ReservationDetailForm(TailwindFormMixin, forms.Form):
    STATUS_CHOICES = Choices(
        ("not_reserved", _("Not Reserved")),
        ("reserved", _("Reserved")),
        ("checked_in", _("Checked In")),
        ("checked_out", _("Checked Out")),
        ("cancelled", _("Cancelled")),
    )
    status = forms.ChoiceField(choices=STATUS_CHOICES)
    price = MoneyField()
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))
    start = forms.DateTimeField(widget=DateInput, label=_("Start"))
    end = forms.DateTimeField(widget=DateInput, label=_("End"))


class StayForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Stay
        fields = [
            "start",
            "end",
        ]
        widgets = {"start": DateInput(), "end": DateInput()}

    do_htmx_validation = True


class ContactInfoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ContactInfo
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": _("First Name"),
            "last_name": _("Last Name"),
            "email": _("Email"),
        }

    do_htmx_validation = True


class SquarePaymentTokenForm(TailwindFormMixin, forms.Form):
    token = forms.CharField(widget=forms.HiddenInput())


class RoomCreateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "room_tier"]

    name = forms.CharField(label=_("Room Name"), max_length=255)

    # pricing_tiers = forms.MultipleChoiceField(
    #     label=_("Pricing Tiers"),
    #     widget=forms.CheckboxSelectMultiple,
    # )
    #
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["pricing_tiers"].choices = [
    #         (choice.id, choice)
    #         for choice in PricingTier.objects.all().order_by("id")
    #         if PricingTier.objects.all().exists()
    #     ]
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.fields["room_tier"].choices = [
    #         (choice.id, choice)
    #         for choice in RoomTier.objects.all().order_by("name")
    #         if RoomTier.objects.all().exists()
    #     ]


class RoomDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name", "room_tier"]

    name = forms.CharField(label=_("Room Name"), max_length=255)


class RoomTierCreateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RoomTier
        fields = ["name"]


class RoomTierDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RoomTier
        fields = ["name"]


class PricingTierCreateForm(forms.ModelForm):
    class Meta:
        model = PricingTier
        fields = ["number_of_adults", "price_overnight", "price_short_term"]
        labels = {
            "number_of_adults": _("Number of Adults"),
            "price_overnight": _("Price overnight"),
            "price_short_term": _("Price Short-term"),
        }


class PricingTierDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = PricingTier
        fields = ["number_of_adults", "price_overnight", "price_short_term"]
        labels = {
            "number_of_adults": _("Number of Adults"),
            "price_overnight": _("Price Overnight"),
            "price_short_term": _("Price Short-term"),
        }


class IncrementalPricingTierFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.minimum_number_of_adults = kwargs.pop("minimum_number_of_adults", 1)
        self.maximum_number_of_adults = kwargs.pop("maximum_number_of_adults", 6)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        initial_number_of_adults = self.minimum_number_of_adults + index
        initial = kwargs.get("initial", {})
        initial["number_of_adults"] = initial_number_of_adults
        kwargs["initial"] = initial
        return kwargs


class PricingTierGroupCreateForm(forms.Form):
    class Meta:
        model = PricingTierGroup
        fields = (
            "name",
            "minimum_number_of_adults",
            "maximum_number_of_adults",
            "room_tiers",
            "campaign",
        )

    name = forms.CharField(max_length=100, label=_("Name"))
    minimum_number_of_adults = forms.IntegerField(
        initial=1, min_value=1, max_value=2, label=_("Minimum Adults")
    )
    maximum_number_of_adults = forms.IntegerField(
        initial=6, min_value=4, max_value=6, label=_("Maximum Adults")
    )
    price_overnight_child = MoneyField()
    price_short_term_child = MoneyField()
    room_tiers = forms.ModelMultipleChoiceField(
        queryset=RoomTier.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_("Room Tiers"),
    )
    campaigns = forms.ModelChoiceField(
        queryset=Campaign.objects.all(),
        required=False,
        label=_("Campaigns"),
    )


# class PricingTierGroupDetailForm(forms.ModelForm):
#     class Meta:
#         model = PricingTierGroup
#         fields = ["name", "room_tiers", "campaigns"]
#         widgets = {"campaigns": forms.CheckboxSelectMultiple}


class PricingTierGroupDetailForm(forms.ModelForm):
    class Meta:
        model = PricingTierGroup
        fields = (
            "name",
            "minimum_number_of_adults",
            "maximum_number_of_adults",
            "room_tiers",
            "campaign",
        )

    name = forms.CharField(max_length=100, label=_("Name"))
    minimum_number_of_adults = forms.IntegerField(
        initial=1, min_value=1, max_value=2, label=_("Minimum Adults")
    )
    maximum_number_of_adults = forms.IntegerField(
        initial=6, min_value=4, max_value=6, label=_("Maximum Adults")
    )
    room_tiers = forms.ModelMultipleChoiceField(
        queryset=RoomTier.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label=_("Room Tiers"),
    )
    campaign = forms.ModelChoiceField(
        queryset=Campaign.objects.all(),
        required=False,
        label=_("Campaign"),
    )


class CampaignCreateForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "recurrences"]


class CampaignDetailForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "recurrences"]


class VendorCreateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Vendor
        exclude = ["account"]
        help_texts = {
            "due_day": _(
                "This value is additive. Example: If the cutoff day results in a cutoff *date* of 2024-5-10, and the due day here is 10, then the due day will result in a due date of 2024-5-20. A value of -1 will result in 'end of the month' value. If the cutoff date is 2024-5-10 and due day here is -1, then the due date will be 2024-5-31."
            )
        }


class VendorDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Vendor
        exclude = []
        help_texts = {
            "due_day": _(
                "This value is additive. Example: If the cutoff day results in a cutoff *date* of 2024-5-10, and the due day here is 10, then the due day will result in a due date of 2024-5-20. A value of -1 will result in 'end of the month' value. If the cutoff date is 2024-5-10 and due day here is -1, then the due date will be 2024-5-31."
            )
        }


class InvoiceCreateForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["vendor", "invoiced_on", "due_on"]


class InvoiceDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["id"]


class ProcurementCreateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Procurement
        fields = ["vendor", "product", "price_per_unit", "quantity", "procured_on"]
        widgets = {"procured_on": forms.SelectDateWidget()}


class ProcurementCreateForm(TailwindFormMixin, forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.filter(type="LI"), label=_("Account")
    )
    item = forms.ModelChoiceField(queryset=Item.objects.all(), label=_("Item"))
    price_per_unit = MoneyField(label=_("Price Per Unit"))
    quantity = forms.IntegerField(label=_("Quantity"))
    total = MoneyField(label=_("Total"))
    procured_on = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label=_("Procured On")
    )


class ProcurementDetailForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = TransactionDetail
        exclude = []


if not Vendor.objects.all().exists():
    dairy_peddler = "クリームとチーズ牧場"
    DEFAULT_VENDOR = Vendor.objects.create(
        name=dairy_peddler,
        cutoff_day=-1,
        due_day=-1,
        phone=PhoneNumber.from_string("+8107043327278", region="JA"),
        postal_code="064-0941",
        address="2-6-2 Milky Lane",
        city="Sapporo",
        prefecture="Hokkaido",
    )


class CompanyWiseProcurementLedgerFilter(TailwindFormMixin, forms.Form):
    if Vendor.objects.all().exists():
        vendor = forms.ModelChoiceField(
            queryset=Vendor.objects.all(),
            initial=Vendor.objects.first(),
            label=_("Vendor"),
        )
    else:
        vendor = forms.ModelChoiceField(
            queryset=Vendor.objects.all(), initial=DEFAULT_VENDOR, label=_("Vendor")
        )
    current_year = datetime.today().year
    current_month = datetime.today().month
    year = forms.IntegerField(
        max_value=current_year, initial=current_year, label=_("Year")
    )
    month = forms.IntegerField(
        min_value=1, max_value=12, initial=current_month, label=_("Month")
    )


class AccountForm(TailwindFormMixin, account_forms.AccountForm):
    currencies = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple, choices=CURRENCY_CHOICES
    )

    def _check_currencies_json(self):
        pass


# TODO: Grab all of the Hordak forms.


class SimpleTransactionForm(TailwindFormMixin, transaction_forms.SimpleTransactionForm):
    def save(self, commit=True):
        from_account = self.cleaned_data.get("from_account")
        to_account = self.cleaned_data.get("to_account")
        amount = self.cleaned_data.get("amount")

        return from_account.account_transfer_to(
            to_account=to_account,
            amount=amount,
            description=self.cleaned_data.get("description"),
            date=self.cleaned_data.get("date"),
        )
