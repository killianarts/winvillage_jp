import datetime as dt

from django import forms
from django.utils.translation import gettext_lazy as _
from phonenumber_field.formfields import PhoneNumberField

from core.forms import ShisoFormMixin
from reservations.models import Stay


class GrillOptionForm(forms.Form):
    grill_id = forms.IntegerField(widget=forms.HiddenInput)


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class ContactInfoForm(ShisoFormMixin, forms.Form):
    first_name = forms.CharField(
        label=_("First Name"),
    )
    last_name = forms.CharField(
        label=_("Last Name"),
    )
    email = forms.EmailField(
        label=_("Email"),
    )
    phone = PhoneNumberField(
        label=_("Phone #"),
    )


class DateForm(forms.Form):
    date = forms.DateTimeField(widget=forms.HiddenInput)


class StayTypeSelectForm(ShisoFormMixin, forms.Form):
    CHOICES = [("", "---"), ("ST", _("Short-term")), ("ON", _("Overnight"))]
    type = forms.ChoiceField(choices=CHOICES)


class TimeSelectForm(forms.Form):
    DEFAULT_CHOICE = [("", "---")]
    HOURS = []
    for h in range(9, 23):
        HOURS.append((dt.time(hour=h), f"{h}:00"))
        HOURS.append((dt.time(hour=h, minute=30), f"{h}:30"))
    CHOICES = DEFAULT_CHOICE + HOURS
    start_time = forms.ChoiceField(choices=CHOICES)
    end_time = forms.ChoiceField(choices=CHOICES)

    def clean_start_time(self):
        start_time = self.cleaned_data.get("start_time")
        start_time = dt.datetime.strptime(start_time, "%H:%M:%S").time()
        return start_time

    def clean_end_time(self):
        end_time = self.cleaned_data.get("end_time")
        end_time = dt.datetime.strptime(end_time, "%H:%M:%S").time()
        return end_time


class DateTimeForm(forms.Form):
    datetime = forms.DateTimeField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        datetime_widget_id = kwargs.pop("datetime_widget_id", None)
        super().__init__(*args, **kwargs)

        if datetime_widget_id:
            self.fields["datetime"].widget.attrs["id"] = datetime_widget_id


class StartEndDateTimesForm(forms.Form):
    start = forms.DateTimeField(widget=forms.HiddenInput)
    end = forms.DateTimeField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        start_widget_id = kwargs.pop("start_widget_id", None)
        end_widget_id = kwargs.pop("end_widget_id", None)

        super().__init__(*args, **kwargs)

        if start_widget_id:
            self.fields["start"].widget.attrs["id"] = start_widget_id

        if end_widget_id:
            self.fields["end"].widget.attrs["id"] = end_widget_id


class TravelerForm(ShisoFormMixin, forms.ModelForm):
    class Meta:
        model = Stay
        fields = ("number_of_adults", "number_of_children")

    do_htmx_validation = True

    def clean_number_of_adults(self):
        number_of_adults = self.cleaned_data.get("number_of_adults")
        if number_of_adults == "---":
            raise forms.ValidationError(_("Please choose the number of adults."))
        return number_of_adults


# By default, the label for each choice in ModelChoiceField is generated from the model's __str__ method.
# I'm specifying it here explicitly because I rely on that currently for correct template rendering.
# In the template, accessing the label for each choice in the below "rooms" field looks like this:
# {% for radio in form.rooms %}
#  {{ radio.choice_label }}
class RoomChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class RoomTierChoiceForm(forms.Form):
    roomtiers = RoomChoiceField(queryset=None, widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop("queryset", None)
        super(RoomTierChoiceForm, self).__init__(*args, **kwargs)
        self.fields["roomtiers"].queryset = queryset
