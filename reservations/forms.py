from django import forms


class Step1Form(forms.Form):
    CHOICES = (
        ("hourly", "Hourly"),
        ("multi", "Multi"),
    )
    stay_type = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=CHOICES,
        initial="hourly",
    )


class Step2Form(forms.Form):
    CHOICES = (
        ("hourly", "Hourly"),
        ("multi", "Multi"),
    )
    stay_length = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=CHOICES,
        initial="hourly",
    )
