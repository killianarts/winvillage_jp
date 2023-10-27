from django.urls import path

from customer import views as customer
from . import views

app_name = "winadmin"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login_page"),
    path("logout/", views._logout, name="logout"),
    path("inventory/", views.item_list, name="list_inventory"),
    path(
        "inventory/item/<int:pk>/",
        views.item_detail,
        name="edit_inventory_item",
    ),
    path(
        "inventory/item/<int:pk>/delete/",
        views.item_delete,
        name="delete_inventory_item",
    ),
    path(
        "inventory/create/",
        views.item_create,
        name="create_inventory_item_page",
    ),
    path("inventory/category/", views.category_list, name="list_categories_page"),
    path(
        "inventory/category/create/",
        views.category_create,
        name="create_category_page",
    ),
    path(
        "inventory/category/<int:pk>/",
        views.category_edit,
        name="edit_category_page",
    ),
    path("transactions/", views.transaction_list, name="view_all_transactions"),
    # path("transactions/sales/", views.view_sales, name="view_sales"),
    path(
        "transactions/sales/",
        views.sales_list_by_period,
        name="view_sales_by_period",
    ),
    path("transactions/create/", views.transaction_create, name="create_transaction"),
    path(
        "reservations/",
        views.reservation_list_by_period,
        name="view_reservations_by_period",
    ),
    path("reservations/create/", views.reservation_create, name="create_reservation"),
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
        "reservations/edit/<int:pk>/", views.reservation_detail, name="edit_reservation"
    ),
    path("reservations/make-payment/", views.make_payment, name="make_payment"),
    path(
        "reservations/send-confirmation-email/",
        views.send_confirmation_email,
        name="send_confirmation_email",
    ),
    path("customer/create/", customer.customer_create, name="customer_create"),
    path(
        "customer/create-bulk/",
        customer.customer_create_bulk,
        name="customer_create_bulk",
    ),
    path("customer/list/", customer.customer_list, name="customer_list"),
    path(
        "customer/detail/<int:customer_id>/",
        customer.customer_detail,
        name="customer_detail",
    ),
    path("ticket/create/", customer.ticket_create, name="ticket_create"),
    path("ticket/list/", customer.ticket_list, name="ticket_list"),
    path(
        "ticket/detail/<int:ticket_id>/",
        customer.ticket_detail,
        name="ticket_detail",
    ),
]
