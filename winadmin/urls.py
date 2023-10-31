from django.urls import path

from customer import views as customer
from . import views

app_name = "winadmin"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_page, name="login_page"),
    path("logout/", views._logout, name="logout"),
    path("inventory/list/", views.item_list, name="item_list"),
    path(
        "inventory/item/<int:pk>/",
        views.item_detail,
        name="item_detail",
    ),
    path(
        "inventory/item/<int:pk>/delete/",
        views.item_delete,
        name="item_delete",
    ),
    path(
        "inventory/create/",
        views.item_create,
        name="item_create",
    ),
    path("inventory/category/", views.category_list, name="category_list"),
    path(
        "inventory/category/create/",
        views.category_create,
        name="category_create",
    ),
    path(
        "inventory/category/<int:pk>/",
        views.category_detail,
        name="category_detail",
    ),
    path(
        "transactions/list/",
        views.transaction_list_by_period,
        name="transaction_list_by_period",
    ),
    path(
        "transactions/sale/list/",
        views.sale_list_by_period,
        name="sale_list_by_period",
    ),
    path("transactions/create/", views.transaction_create, name="transaction_create"),
    path(
        "reservations/",
        views.reservation_list_by_period,
        name="reservation_list_by_period",
    ),
    path("reservations/create/", views.reservation_create, name="reservation_create"),
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
        "reservations/edit/<int:pk>/",
        views.reservation_detail,
        name="reservation_detail",
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

urlpatterns += [
    path(
        "inventory/", views.inventory_management_page, name="inventory_management_page"
    ),
    path("transactions/sale/", views.sale_management_page, name="sale_management_page"),
    # "inventory/", views.inventory_management_page, name="inventory_management_page"
]
