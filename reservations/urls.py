from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.index, name="index"),
    path("select-time/", views.time_select, name="time_select"),
    path("select-options/", views.option_select, name="option_select"),
    path(
        "contact-information-input/",
        views.contact_information_input,
        name="contact_information_input",
    ),
    path(
        "send-confirmation-email/",
        views.send_confirmation_email,
        name="send_confirmation_email",
    ),
]
