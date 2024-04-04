from django.urls import path
from django.contrib.sitemaps.views import sitemap

from winvillage.sitemaps import StaticViewSitemap
from . import views

app_name = "core"
sitemaps = {"static": StaticViewSitemap}
urlpatterns = [
    path("", views.index, name="homepage"),
    path("rooms/", views.room_details, name="room_details"),
    path("get-messages/", views.get_messages, name="get_messages"),
    path("flush-session/", views.flush_session, name="flush_session"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
]
