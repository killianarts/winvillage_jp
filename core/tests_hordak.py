from djmoney.money import Money
from freezegun import freeze_time
from hordak import models as hordak_models
from djmoney.money import Money
from hordak.utilities import currency
from django.test import TestCase
from django.db import transaction as db_transaction

m1000 = Money(1000, "JPY")

m100 = Money(100, "JPY")


class AccountsAndTransactionsTest(TestCase):
    def setUp(self):
        cow_parts = hordak_models.Account.objects.create(
            name="Tender Cow Parts Peddler", type="LI"
        )
        cog = hordak_models.Account.objects.create(name="Cost of Goods Sold", type="EX")
        inventory = hordak_models.Account.objects.create(name="Inventory", type="AS")
        scrooge = hordak_models.Account.objects.create(name="Scrooges Bank", type="AS")
        mirai = hordak_models.Account.objects.create(
            name="Mirai Receivables", type="AS"
        )
        cash = hordak_models.Account.objects.create(name="Cold Hard Cash", type="AS")
        sales = hordak_models.Account.objects.create(name="Store Sales", type="IN")

    # def test_buy_inventory(self):
    #     print("")
    #     print("--------------------------------------------------")
    #     print("Buy Inventory Pay Later | LI -> AS")
    #     print("--------------------------------------------------")
    #     cow_parts = hordak_models.Account.objects.get(name="Tender Cow Parts Peddler")
    #     sold = hordak_models.Account.objects.get(name="Cost of Goods Sold")
    #     inventory = hordak_models.Account.objects.get(name="Inventory")
    #     scrooge = hordak_models.Account.objects.get(name="Scrooges Bank")
    #     transaction2 = cow_parts.accounting_transfer_to(inventory, m1000)
    #     print(cow_parts)
    #     print(sold)
    #     print(inventory)
    #     print("--------------------------------------------------")
    #     self.assertEqual(cow_parts.balance(), currency.Balance(1000, "JPY"))

    # def test_make_cash_sale_at_register(self):
    #     print("")
    #     print("--------------------------------------------------")
    #     print("Make Cash Sale At Register | IN -> IN")
    #     print("--------------------------------------------------")
    #     sales = hordak_models.Account.objects.get(name="Store Sales")
    #     cash = hordak_models.Account.objects.get(name="Cold Hard Cash")
    #     inventory = hordak_models.Account.objects.get(name="Inventory")
    #     transaction = sales.accounting_transfer_to(cash, m1000 * 5)
    #     print(sales)
    #     print(cash)
    #     print(inventory)
    #     print("--------------------------------------------------")
    #     self.assertEqual(cash.balance(), currency.Balance(5000, "JPY"))

    def test_buy_inventory_then_make_sale_then_pay_invoice(self):
        print("")
        print("--------------------------------------------------")
        print("Buy inventory then make sale then pay invoice")
        print("--------------------------------------------------")
        sales = hordak_models.Account.objects.get(name="Store Sales")
        cog = hordak_models.Account.objects.get(name="Cost of Goods Sold")
        cash = hordak_models.Account.objects.get(name="Cold Hard Cash")
        inventory = hordak_models.Account.objects.get(name="Inventory")
        cow_parts = hordak_models.Account.objects.get(name="Tender Cow Parts Peddler")
        scrooge = hordak_models.Account.objects.get(name="Scrooges Bank")
        mirai = hordak_models.Account.objects.get(name="Mirai Receivables")
        print(sales, hordak_models.Account.TYPES[sales.type])
        print(cog)
        print(cash)
        print(inventory)
        print(cow_parts)

        print("")
        print("-------------------------Buy Inventory-------------------------")
        cow_parts.accounting_transfer_to(inventory, m1000 * 10)
        print(sales)
        print(cog)
        print(cash)
        print(mirai)
        print(inventory)
        print(cow_parts)
        print(scrooge)

        print("")
        print("-----------------------Make Sale via Cash---------------------------")
        get_cash = sales.accounting_transfer_to(cash, m1000 * 7)
        decrease_inventory = inventory.accounting_transfer_to(cog, m1000 * 5)
        print(sales)
        print(cog)
        print(cash)
        print(mirai)
        print(inventory)
        print(cow_parts)
        print(scrooge)

        print("")
        print("-----------------------Make Sale via Card---------------------------")
        get_receivable = sales.accounting_transfer_to(mirai, m1000 * 7)
        decrease_inventory = inventory.accounting_transfer_to(cog, m1000 * 5)
        print(sales)
        print(cog)
        print(cash)
        print(mirai)
        print(inventory)
        print(cow_parts)
        print(scrooge)

        print("")
        print(
            "-----------------------Transfer cash to bank account-----------------------"
        )
        cash.accounting_transfer_to(scrooge, m1000 * 7)
        print(sales)
        print(cog)
        print(cash)
        print(mirai)
        print(inventory)
        print(cow_parts)
        print(scrooge)

        print("")
        print("-----------------------Pay Invoice-----------------------")
        scrooge.accounting_transfer_to(cow_parts, m1000 * 10)
        print(sales)
        print(cog)
        print(cash)
        print(mirai)
        print(inventory)
        print(cow_parts)
        print(scrooge)

        print("")
        print("-----------------------Profit-----------------------")
        print(f"Sales - Cost = {sales.balance() - cog.balance()}")
