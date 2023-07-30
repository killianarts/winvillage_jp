from django.urls import path
from . import views
app_name = "reservations"

urlpatterns = [
    path("test/", views.test, name="test"),
    path("", views.index, name="reservations_index"),
    path("step-1/", views.step_1, name="step-1"),
    path("step-2/", views.step_2, name="step-2"),
]

