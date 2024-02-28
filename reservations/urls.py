from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.index, name="index"),
    path("date-select", views.date_select, name="date_select"),
    path("room-select", views.room_select, name="room_select"),
    path("option-select/", views.option_select, name="option_select"),
    path("times/", views.times_view, name="times_view"),
    path(
        "contact-information-input/",
        views.contact_information_input,
        name="contact_information_input",
    ),
    path(
        "reservation-details-review/",
        views.reservation_details_review,
        name="reservation_details_review",
    ),
    path(
        "reservation-confirm/",
        views.reservation_confirm,
        name="reservation_confirm",
    ),
]
