from django.urls import path
from . import views

app_name = "winadmin"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login_page"),
    path("logoout/", views._logout, name="logout"),
    path("inventory/", views.list_inventory, name="list_inventory"),
    path(
        "inventory/item/<int:pk>/",
        views.view_inventory_item,
        name="view_inventory_item",
    ),
    path(
        "inventory/create/",
        views.create_inventory_item_page,
        name="create_inventory_item_page",
    ),
    path(
        "inventory/category/", views.list_categories_page, name="list_categories_page"
    ),
    path(
        "inventory/category/create/",
        views.create_category_page,
        name="create_category_page",
    ),
]
