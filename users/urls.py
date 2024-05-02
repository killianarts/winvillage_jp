from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    # path("~redirect/", views.user_redirect_view, name="redirect"),
    # path("~update/", views.user_update_view, name="update"),
    # path("<str:username>/", views.user_detail_view, name="detail"),
    path("login_page/", views.login_page, name="login_page"),
    path("logout/", views._logout, name="logout"),
]
