from django.db import transaction as db_transaction
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money
from hordak.models import Account
from winvillage import settings

from core.models import TransactionDetail


def get_account(code):
    return Account.objects.get(code=code)


def get_sales_account_from_configuration(code=300):
    account = get_account(code=code)
    assert account.type == "IN"
    return account


def get_cash_account_from_configuration(code=100):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_accounts_receivable_account_from_configuration(code=110):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_inventory_account_from_configuration(code=120):
    account = get_account(code=code)
    assert account.type == "AS"
    return account


def get_cogs_account_from_configuration(code=400):
    account = get_account(code=code)
    assert account.type == "EX"
    return account


def get_accounts_payable_account_from_configuration(code=200):
    account = get_account(code=code)
    assert account.type == "LI"
    return account


# class Money(DefaultMoney):
#     def __init__(self, amount: object = 0, currency: str | None = None) -> None:
#         super().__init__(
#             amount=amount,
#             currency=settings.DEFAULT_CURRENCY[0] if currency is None else currency,
#         )


def create_sales_from_order(order_obj, payment_type=None):
    with db_transaction.atomic():
        details = []
        sales_account = get_sales_account_from_configuration()
        if payment_type == "cash":
            to_account = get_cash_account_from_configuration()
        else:
            to_account = get_accounts_receivable_account_from_configuration()
        for orderitem in order_obj.items.all():
            transaction = sales_account.accounting_transfer_to(
                to_account, orderitem.item.price * orderitem.quantity
            )
            detail = TransactionDetail.objects.create(
                summary=transaction,
                item=orderitem.item.name,
                quantity=orderitem.quantity,
                price_per_unit=orderitem.item.price,
            )
            details.append(detail)
        return details


def create_default_chart_of_accounts():
    cash, created = Account.objects.get_or_create(code=100, name=_("Cash"), type="AS")
    accounts_receivable, created = Account.objects.get_or_create(
        code=110, name=_("Accounts Receivable"), type="AS"
    )
    inventory, created = Account.objects.get_or_create(
        code=120, name=_("Inventory"), type="AS"
    )
    accounts_payable, created = Account.objects.get_or_create(
        code=200, name=_("Accounts Payable"), type="LI"
    )
    taxes_payable, created = Account.objects.get_or_create(
        code=210, name=_("Taxes Payable"), type="LI"
    )
    sales, created = Account.objects.get_or_create(code=300, name=_("Sales"), type="IN")
    cost_of_goods_sold, created = Account.objects.get_or_create(
        code=400, name=_("Cost of Goods Sold"), type="EX"
    )
    return [
        cash,
        accounts_receivable,
        inventory,
        accounts_payable,
        taxes_payable,
        sales,
        cost_of_goods_sold,
    ]
