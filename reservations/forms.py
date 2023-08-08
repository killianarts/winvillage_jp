from django import forms
from django.utils.translation import gettext_lazy as _
from reservations.models import Stay


class Step1Form(forms.Form):
    CHOICES = (
        ("hourly", _("Hourly")),
        ("overnight", _("Overnight")),
    )
    stay_type = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=CHOICES,
        initial="hourly",
    )


class DateInput(forms.DateInput):
    input_type = "date"


# class Step2Form(forms.Form):
#     stay_date_start = forms.DateField(widget=DateInput, label=_("From"))
#     stay_date_end = forms.DateField(widget=DateInput, label=_("Until"))


class Step2Form(forms.ModelForm):
    class Meta:
        model = Stay
        fields = ["start_datetime", "end_datetime"]
        widgets = {
            "start_datetime": DateInput(),
            "end_datetime": DateInput(),
        }


class Step3Form(forms.Form):
    grill = forms.BooleanField(label=_("Grill"), required=False)
    food = forms.BooleanField(label=_("Food"), required=False)


class Step4Form(forms.Form):
    first_name = forms.CharField(max_length=255, label=_("First Name"))
    last_name = forms.CharField(max_length=255, label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))


class ConfirmationForm(forms.Form):
    stay_date_start = forms.DateField(widget=DateInput, label=_("From"))
    stay_date_end = forms.DateField(widget=DateInput, label=_("Until"))
    purchase_grill = forms.BooleanField(label=_("Grill"), required=False)
    purchase_food = forms.BooleanField(label=_("Food"), required=False)
    first_name = forms.CharField(max_length=255, label=_("First Name"))
    last_name = forms.CharField(max_length=255, label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))
