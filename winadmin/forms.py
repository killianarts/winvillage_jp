from django import forms
from django.utils.translation import gettext_lazy as _
from core.models import Item, Category, Transaction


class LoginForm(forms.Form):
    username = forms.CharField(label=_("Username"), max_length=30)
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, max_length=30
    )


class CreateItemForm(forms.ModelForm):
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
            "description",
            "short_description",
        ]


class EditItemForm(forms.ModelForm):
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
            "description",
            "short_description",
        ]


class CreateCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            "title",
        ]


class CreateTransactionForm(forms.ModelForm):
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


class SetLedgerPeriodForm(forms.Form):
    year = forms.IntegerField()
    month = forms.IntegerField()
