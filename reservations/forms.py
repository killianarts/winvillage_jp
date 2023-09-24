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

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


# class Step2Form(forms.Form):
#     stay_date_start = forms.DateField(widget=DateInput, label=_("From"))
#     stay_date_end = forms.DateField(widget=DateInput, label=_("Until"))


class Step2Form(forms.ModelForm):
    class Meta:
        model = Stay
        fields = ["start_datetime", "end_datetime"]
        labels = {"start_datetime": _("From"), "end_datetime": _("Until")}
        widgets = {
            "start_datetime": DateInput(),
            "end_datetime": DateInput(),
        }


class Step4Form(forms.Form):
    first_name = forms.CharField(max_length=255, label=_("First Name"))
    last_name = forms.CharField(max_length=255, label=_("Last Name"))
    email = forms.EmailField(label=_("Email"))


# class StayFormSet(
#     forms.inlineformset_factory(Reservation, Stay, form=Step2Form, extra=1)
# ):
#     pass
#
#
# class ContactInfoFormSet(
#     forms.inlineformset_factory(Reservation, ContactInfo, form=Step4Form, extra=1)
# ):
#     pass


# class ConfirmationForm(forms.ModelForm):
#     stay_form = StayFormSet()
#     contact_info_form = ContactInfoFormSet()
#
#     class Meta:
#         model = Reservation
#         fields = ["stay", "contact_info"]
