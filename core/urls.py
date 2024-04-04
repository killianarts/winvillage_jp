from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.index, name="index"),
    path("rooms/", views.room_details, name="room_details"),
    path("get-messages/", views.get_messages, name="get_messages"),
    path("flush-session/", views.flush_session, name="flush_session"),
]
