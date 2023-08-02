from django import forms
from django.utils.translation import gettext_lazy as _


class Step1Form(forms.Form):
    CHOICES = (
        ("hourly", _("Hourly")),
        ("multi", _("Multi")),
    )
    stay_type = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=CHOICES,
        initial="hourly",
    )


class DateInput(forms.DateInput):
    input_type = "date"


class Step2Form(forms.Form):
    stay_date_start = forms.DateField(widget=DateInput, label=_("From:"))
    stay_date_end = forms.DateField(widget=DateInput, label=_("Until:"))


class Step3Form(forms.Form):
    purchase_grill = forms.BooleanField(label=_("Grill"), required=False)
    purchase_food = forms.BooleanField(label=_("Food"), required=False)
