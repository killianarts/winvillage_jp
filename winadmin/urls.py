from django.urls import path

from customer import views as customer
from . import views

app_name = "winadmin"

urlpatterns = [
    path("", views.index, name="index"),
    path("inventory/list/", views.item_list, name="item_list"),
    path(
        "inventory/item/<int:pk>/",
        views.item_detail,
        name="item_detail",
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
    path("sales/ledger/", views.sales_ledger, name="sales_ledger"),
    path(
        "sales/accounts_receivable_ledger/",
        views.accounts_receivable_ledger,
        name="accounts_receivable_ledger",
    ),
    path(
        "transactions/list/",
        views.transaction_list_by_period,
        name="transaction_list_by_period",
    ),
    path(
        "transactions/export",
        views.transaction_export_csv_by_period,
        name="transaction_export_csv_by_period",
    ),
    path("transactions/create/", views.transaction_create, name="transaction_create"),
    path(
        "transactions/detail/<int:id>/",
        views.transaction_detail,
        name="transaction_detail",
    ),
    path(
        "reservations/list/",
        views.reservation_list_by_period,
        name="reservation_list_by_period",
    ),
    path("reservations/create/", views.reservation_create, name="reservation_create"),
    path(
        "reservations/create/contact-information-input/",
        views.contact_information_input,
        name="contact_information_input",
    ),
    path(
        "reservations/create/datetime-select/",
        views.datetime_select,
        name="datetime_select",
    ),
    path(
        "reservations/create/option-select/", views.option_select, name="option_select"
    ),
    path("reservations/create/update-price/", views.update_price, name="update_price"),
    path(
        "reservations/detail/<int:pk>/",
        views.reservation_detail,
        name="reservation_detail",
    ),
    path("reservations/make-payment/", views.make_payment, name="make_payment"),
    path(
        "reservations/send-confirmation-email/",
        views.send_confirmation_email,
        name="send_confirmation_email",
    ),
    path(
        "campaign/create/",
        views.campaign_create,
        name="campaign_create",
    ),
    path(
        "campaign/list/",
        views.campaign_list,
        name="campaign_list",
    ),
    path(
        "campaign/detail/<int:campaign_id>/",
        views.campaign_detail,
        name="campaign_detail",
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
    path(
        "customer/check-in-check-out/",
        views.customer_check_in_check_out_list,
        name="customer_check_in_check_out_list",
    ),
    path(
        "customer/check-in-check-out/<int:reservation_id>",
        views.customer_check_in_check_out_detail,
        name="customer_check_in_check_out_detail",
    ),
    path(
        "customer/occupied-rooms/",
        customer.occupied_room_list,
        name="occupied_room_list",
    ),
    path(
        "customer/purchase/<int:room_id>/<int:customer_id>",
        customer.checked_in_customer_purchase,
        name="checked_in_customer_purchase",
    ),
    path(
        "customer/return/<int:room_id>/<int:customer_id>",
        customer.checked_in_customer_return,
        name="checked_in_customer_return",
    ),
    path("ticket/create/", customer.ticket_create, name="ticket_create"),
    path("ticket/list/", customer.ticket_list, name="ticket_list"),
    path(
        "ticket/detail/<int:ticket_id>/",
        customer.ticket_detail,
        name="ticket_detail",
    ),
    path("room/create/", views.room_create, name="room_create"),
    path("room/list/", views.room_list, name="room_list"),
    path(
        "room/detail/<int:room_id>/",
        views.room_detail,
        name="room_detail",
    ),
    path("room_tier/create/", views.room_tier_create, name="room_tier_create"),
    path("room_tier/list/", views.room_tier_list, name="room_tier_list"),
    path(
        "room_tier/detail/<int:room_tier_id>/",
        views.room_tier_detail,
        name="room_tier_detail",
    ),
    path("pricing_tier/create/", views.pricing_tier_create, name="pricing_tier_create"),
    path("pricing_tier/list/", views.pricing_tier_list, name="pricing_tier_list"),
    path(
        "pricing_tier/detail/<int:pricing_tier_id>/",
        views.pricing_tier_detail,
        name="pricing_tier_detail",
    ),
    path(
        "pricing_tier_group/create/",
        views.pricing_tier_group_create,
        name="pricing_tier_group_create",
    ),
    path(
        "pricing_tier_group/list/",
        views.pricing_tier_group_list,
        name="pricing_tier_group_list",
    ),
    path(
        "pricing_tier_group/detail/<int:pricing_tier_group_id>/",
        views.pricing_tier_group_detail,
        name="pricing_tier_group_detail",
    ),
    path("vendor/create/", views.vendor_create, name="vendor_create"),
    path("vendor/list/", views.vendor_list, name="vendor_list"),
    path("vendor/detail/<int:vendor_id>/", views.vendor_detail, name="vendor_detail"),
    path("invoice/create/", views.invoice_create, name="invoice_create"),
    path("procurement/invoice/list/", views.invoice_list, name="invoice_list"),
    path(
        "procurement/invoice/<int:invoice_id>/",
        views.invoice_detail,
        name="invoice_detail",
    ),
    path("procurement/create/", views.procurement_create, name="procurement_create"),
    path("procurement/list/", views.procurement_list, name="procurement_list"),
    path(
        "procurement/company_wise_procurement_ledger/",
        views.company_wise_procurement_ledger,
        name="company_wise_procurement_ledger",
    ),
    path(
        "procurement/accounts_payable_ledger/",
        views.accounts_payable_ledger,
        name="accounts_payable_ledger",
    ),
    path(
        "procurement/accounts_payable_aging_report/",
        views.accounts_payable_aging_report,
        name="accounts_payable_aging_report",
    ),
    path(
        "procurement/detail/<int:procurement_id>/",
        views.procurement_detail,
        name="procurement_detail",
    ),
    path(
        "accounting/business_account/create/",
        views.business_account_create,
        name="business_account_create",
    ),
    path(
        "accounting/business_account/list/",
        views.business_account_list,
        name="business_account_list",
    ),
    path(
        "accounting/business_account/detail/<int:business_account_id>/",
        views.business_account_detail,
        name="business_account_detail",
    ),
    path(
        "accounting/business_transaction/create/",
        views.business_transaction_create,
        name="business_transaction_create",
    ),
    path(
        "accounting/business_transaction/list/",
        views.business_transaction_list,
        name="business_transaction_list",
    ),
]

urlpatterns += [
    path(
        "inventory/", views.inventory_management_page, name="inventory_management_page"
    ),
    path("transactions/sale/", views.sale_management_page, name="sale_management_page"),
]
