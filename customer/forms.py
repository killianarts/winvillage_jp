from core.forms import ReadOnlyFormMixin, TailwindFormMixin
from core.models import Category, Item
from django import forms
from django.forms import modelformset_factory
from django.forms.renderers import TemplatesSetting
from django.utils.translation import gettext_lazy as _
from djmoney.forms import MoneyField
from phonenumber_field.formfields import PhoneNumberField
from reservations.models import OrderItem

from customer.models import Customer


class CustomerDetailForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))

    do_htmx_validation = True


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


class CustomerCheckInForm(TailwindFormMixin, forms.Form):
    first_name = forms.CharField(label=_("First Name"))
    last_name = forms.CharField(label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
    phone = PhoneNumberField(label=_("Phone #"))

    do_htmx_validation = False


class CustomerForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["first_name", "last_name", "email", "phone"]


class ItemForm(forms.Form):
    item_id = forms.IntegerField(widget=forms.HiddenInput())
    name = forms.CharField(label=_("Name"))
    price = MoneyField(label=_("Price"))
    quantity = forms.IntegerField(label=_("Quantity"), min_value=0)


# class ItemForm(TailwindFormMixin, forms.ModelForm):
#     class Meta:
#         model = Item
#         fields = ["id", "name", "price"]

# quantity = forms.IntegerField(label=_("Quantity"), min_value=0)


# class ItemFormRenderer(TemplatesSetting):
#     form_template_name = "core/forms/tailwind/div.html"
#     formset_template_name = "core/forms/formsets/div.html"
#     single_field_row_template = "core/forms/formsets/formset_field_row.html"
#     field_template_name = "core/forms/tailwind/field_row_read_only.html"
#
#
# class ItemFormMixin(TemplatesSetting):
#     default_renderer = ItemFormRenderer()
#
#     # def __init__(self, *args, **kwargs) -> None:
#     # We don’t want ':' as a label suffix:
#     # return super().__init__(*args, label_suffix="", **kwargs)
#
#     def get_context(self, *args, **kwargs):
#         return super().get_context(*args, **kwargs) | {
#             "single_field_row_template": self.renderer.single_field_row_template,
#         }
#
#
# class ItemForm(ItemFormMixin, forms.ModelForm):
#     # default_renderer = ItemFormRenderer()
#
#     class Meta:
#         model = Item
#         fields = ["id", "name", "price"]
#
#     quantity = forms.DecimalField(label=_("Quantity"), min_value=0)
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Initialize the quantity_in_order field with the annotated value from the model instance
#         if self.instance:
#             self.fields["quantity"].initial = self.instance.quantity_in_order
#
#     def save(self, commit=False):
#         # Custom save method to handle the quantity_in_order field
#         instance = super().save(commit=False)
#         # Find the related OrderItem instances for the current Item
#         order_item, created = OrderItem.objects.get_or_create(item=self.instance)
#         # Update the quantity field of each related OrderItem with the form's value
#         quantity = self.cleaned_data.get("quantity")
#         if quantity > 0:
#             order_item.quantity = quantity
#             order_item.save()
#             instance.save()
#         else:
#             order_item.delete()
#
#
# ItemFormSet = modelformset_factory(Item, form=ItemForm, extra=0)


class CategoryFilterForm(forms.Form):
    categories = forms.ChoiceField(
        choices=[("0", "All")]
        + [(category.id, category.name) for category in Category.objects.all()],
        widget=forms.RadioSelect(),
        initial="0",
    )
