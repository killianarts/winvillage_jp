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
        views.edit_inventory_item,
        name="edit_inventory_item",
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
    path("transactions/", views.view_all_transactions, name="view_all_transactions"),
    # path("transactions/sales/", views.view_sales, name="view_sales"),
    path(
        "transactions/sales/",
        views.view_sales_by_period,
        name="view_sales_by_period",
    ),
    path("transactions/create/", views.create_transaction, name="create_transaction"),
    path(
        "reservations/",
        views.view_reservations_by_period,
        name="view_reservations_by_period",
    ),
    path("reservations/create/", views.create_reservation, name="create_reservation"),
    path(
        "reservations/create/add-option/<int:pk>/",
        views.add_grill_reservation_option,
        name="add_grill_reservation_option",
    ),
    path(
        "reservations/create/remove-option/<int:pk>/",
        views.remove_grill_reservation_option,
        name="remove_grill_reservation_option",
    ),
    path("reservations/create/update-price/", views.update_price, name="update_price"),
    path(
        "reservations/edit/<int:pk>/", views.edit_reservation, name="edit_reservation"
    ),
]
