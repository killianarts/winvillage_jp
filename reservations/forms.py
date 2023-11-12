from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import RegionalPhoneNumberWidget

from core.forms import TailwindFormMixin, ReservationsContactInformationFormMixin
from reservations.models import Stay


class GrillOptionForm(forms.Form):
    grill_id = forms.IntegerField(widget=forms.HiddenInput)


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
        widgets = {
            "start_datetime": DateInput(),
            "end_datetime": DateInput(),
        }


class Step2Form(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Stay
        fields = ["start_datetime", "end_datetime"]
        widgets = {
            "start_datetime": DateInput(),
            "end_datetime": DateInput(),
        }


class Step2FormHourly(TailwindFormMixin, forms.ModelForm):
    date = forms.DateField(widget=forms.widgets.DateInput, label=_("Date"))
    start_time = forms.TimeField(
        widget=forms.widgets.TimeInput(format="%H:%M"), label=_("Start Time")
    )
    end_time = forms.TimeField(
        widget=forms.widgets.TimeInput(format="%H:%M"), label=_("End Time")
    )

    class Meta:
        model = Stay
        fields = []

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")

        # Check if none of the fields has been cleaned then return empty dict.
        if date is None or start_time is None or end_time is None:
            return cleaned_data

        # Construct datetime values
        from datetime import datetime

        cleaned_data["start_datetime"] = datetime.combine(date, start_time)
        cleaned_data["end_datetime"] = datetime.combine(date, end_time)

        if cleaned_data["end_datetime"] <= cleaned_data["start_datetime"]:
            raise ValidationError(
                _("End time must be after start time"),
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_datetime = self.cleaned_data.get("start_datetime")
        instance.end_datetime = self.cleaned_data.get("end_datetime")

        if commit:
            instance.save()
        return instance


class ContactInfoForm(ReservationsContactInformationFormMixin, forms.Form):
    first_name = forms.CharField(
        max_length=255,
        label=_("First Name"),
        # widget=forms.TextInput(
        #     attrs={
        #         "hx-post": "contact-information-input/",
        #         "hx-target": "#reservation-form-wrapper",
        #         "hx-swap": "innerHTML",
        #         "hx-trigger": "input delay:250ms",
        #         "hx-vals": '{"use_block": "contact-information-input"}',
        #     }
        # ),
    )
    last_name = forms.CharField(
        max_length=255,
        label=_("First Name"),
        # widget=forms.EmailInput(
        #     attrs={
        #         "hx-post": "contact-information-input/",
        #         "hx-target": "#reservation-form-wrapper",
        #         "hx-swap": "innerHTML",
        #         "hx-trigger": "input delay:250ms",
        #         "hx-vals": '{"use_block": "contact-information-input"}',
        #     }
        # ),
    )
    email = forms.EmailField(
        label=_("Email"),
        # widget=forms.TextInput(
        #     attrs={
        #         "hx-post": "contact-information-input/",
        #         "hx-target": "#reservation-form-wrapper",
        #         "hx-swap": "innerHTML",
        #         "hx-trigger": "input delay:250ms",
        #         "hx-vals": '{"use_block": "contact-information-input"}',
        #     }
        # ),
    )
    phone = PhoneNumberField(
        label=_("Phone #"),
        # widget=RegionalPhoneNumberWidget(
        #     attrs={
        #         "hx-post": "contact-information-input/",
        #         "hx-target": "#reservation-form-wrapper",
        #         "hx-swap": "innerHTML",
        #         "hx-trigger": "input delay:250ms",
        #         "hx-vals": '{"use_block": "contact-information-input"}',
        #     }
        # ),
    )

    do_htmx_validation = True


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


class DateForm(forms.Form):
    date = forms.DateField(widget=forms.HiddenInput)
