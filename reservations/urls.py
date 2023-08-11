from django.urls import path
from . import views

app_name = "reservations"

urlpatterns = [
    # path("test/", views.test, name="test"),
    path("", views.index, name="index"),
    path("step-1/", views.step_1, name="step-1"),
    path("step-2/", views.step_2, name="step-2"),
    path("step-3/", views.step_3, name="step-3"),
    path(
        "add-grill/<int:pk>",
        views.add_grill_reservation_option,
        name="add_grill",
    ),
    path(
        "remove-grill/<int:pk>",
        views.remove_grill_reservation_option,
        name="remove_grill",
    ),
    path("step-4/", views.step_4, name="step-4"),
    path("confirm-reservation/", views.confirm_reservation, name="confirm_reservation"),
    path("pay/", views.payment_page, name="payment_page"),
    path("make-payment/", views.make_payment, name="make_payment"),
    path(
        "send-confirmation-email/",
        views.send_confirmation_email,
        name="send_confirmation_email",
    ),
]
