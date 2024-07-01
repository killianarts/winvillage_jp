import pendulum
from django.db import transaction as db_transaction
from django.utils.timezone import get_default_timezone
from djmoney.money import Money
from hordak.models import Account, Leg
from phonenumber_field.phonenumber import PhoneNumber

from core.accounting_utils import (
    create_default_chart_of_accounts,
    get_inventory_account_from_configuration,
)
from core.models import (
    Category,
    Item,
    TransactionDetail,
    Vendor,
    get_cash_account_from_configuration,
)

cheese = "チーズ"
meat = "佐賀牛"
drink = "ビール"
dairy_peddler = "クリームとチーズ牧場"
beef_peddler = "柔らか牛パーツ"
drink_peddler = "株式会社水分補給ヒーローズ"


jan = pendulum.date(2024, 1, 1)
feb = jan.add(months=1)
mar = jan.add(months=2)
apr = jan.add(months=3)
may = jan.add(months=4)
jun = jan.add(months=5)
jul = jan.add(months=6)


def create_test_vendors():
    dairy_peddler_instance = Vendor.objects.create(
        name=dairy_peddler,
        cutoff_day=-1,
        due_day=-1,
        phone=PhoneNumber.from_string("+8107043327278", region="JA"),
        postal_code="064-0941",
        address="2-6-2 Milky Lane",
        city="Sapporo",
        prefecture="Hokkaido",
    )
    beef_peddler_instance = Vendor.objects.create(
        name=beef_peddler,
        cutoff_day=15,
        due_day=-1,
        phone=PhoneNumber.from_string("+8107043327278", region="JA"),
        postal_code="064-0941",
        address="5-3-8 Beefy Heights",
        city="Kobe",
        prefecture="Hyogo",
    )
    drink_peddler_instance = Vendor.objects.create(
        name=drink_peddler,
        cutoff_day=5,
        due_day=12,
        phone=PhoneNumber.from_string("+8107043327278", region="JA"),
        postal_code="064-0941",
        address="9-9-9 Hydration Park",
        city="Tokyo",
        prefecture="Tokyo",
    )
    return [dairy_peddler_instance, beef_peddler_instance, drink_peddler_instance]


def create_test_items():
    food, _ = Category.objects.get_or_create(name="食べ物")
    drinks, _ = Category.objects.get_or_create(name="飲み物")
    Item.objects.get_or_create(
        name=meat,
        price=Money(5000, "JPY"),
        category=food,
        stock_quantity=50,
        description="脂肪が多い牛肉。",
        short_description="高い牛肉",
    )
    Item.objects.get_or_create(
        name=drink,
        price=Money(200, "JPY"),
        category=drinks,
        stock_quantity=50,
        description="とても美味しいアルコホールの飲み物",
        short_description="朝日",
    )
    Item.objects.get_or_create(
        name=cheese,
        price=Money(500, "JPY"),
        category=food,
        stock_quantity=50,
        description="チェダーの色をしているけど違う",
        short_description="溶ける",
    )
    Item.objects.get_or_create(
        name="ポカリスエット",
        price=Money(200, "JPY"),
        category=drinks,
        stock_quantity=50,
        description="英語で言うとあまり美味しそうじゃない",
        short_description="美味しいシュワシュワ",
    )
    Item.objects.get_or_create(
        name="カボチャ",
        price=Money(500, "JPY"),
        category=food,
        stock_quantity=50,
        description="焼肉と一緒に食べよう",
        short_description="オレンジ",
    )
    Item.objects.get_or_create(
        name="ステーキ",
        price=Money(2500, "JPY"),
        category=food,
        stock_quantity=50,
        description="アメリカ産のステーキ",
        short_description="もお",
    )
    Item.objects.get_or_create(
        name="クリーム",
        price=Money(1500, "JPY"),
        category=drinks,
        stock_quantity=50,
        description="コーヒーに入れるとコーヒーを飲めるようになる",
        short_description="白い",
    )


def create_test_procurement(
    vendor,
    item_name,
    date,
    quantity=5,
):
    if not date:
        date = pendulum.today().start_of("month").date()
    inventory = get_inventory_account_from_configuration()
    accounts_payable = vendor.account
    item = Item.objects.get(name=item_name)
    transaction = accounts_payable.accounting_transfer_to(
        to_account=inventory, amount=quantity * item.price, date=date
    )
    detail, _ = TransactionDetail.objects.get_or_create(
        summary=transaction,
        item=item.name,
        quantity=quantity,
        price_per_unit=item.price,
        type="PR",
    )
    item.stock_quantity += quantity
    return detail


def create_test_procurements_for_vendor(vendor, item_name, start, end, quantity=5):
    start = start.add(days=1)
    interval = pendulum.interval(start, end)
    dates = interval.range("days")
    for date in dates:
        create_test_procurement(vendor, item_name, date, quantity)

    return TransactionDetail.objects.filter(
        summary__legs__account=vendor.account,
        summary__date__range=(start, end),
        type="PR",
    )


def create_procurement_lifecycle(name, item, month, do_pay=True):
    vendor = Vendor.objects.get(name=name)
    cutoff_date = vendor.get_cutoff_date(month)
    previous_cutoff_date = vendor.get_cutoff_date(month.subtract(months=1))
    procurements = create_test_procurements_for_vendor(
        vendor, item, previous_cutoff_date, cutoff_date
    )
    invoice = vendor.create_invoice(cutoff_date, procurements)
    if do_pay:
        cash = Account.objects.get(code=100)
        payment = cash.accounting_transfer_to(
            vendor.account, invoice.amount, date=cutoff_date.add(months=1)
        )
        detail, _ = TransactionDetail.objects.get_or_create(
            summary=payment,
            item=f"Payment to {vendor.name}",
            price_per_unit=invoice.amount,
            quantity=1,
            type="PA",
        )


def init_test_data():
    create_procurement_lifecycle(dairy_peddler, cheese, jan)
    create_procurement_lifecycle(dairy_peddler, cheese, feb)
    create_procurement_lifecycle(dairy_peddler, cheese, mar)
    create_procurement_lifecycle(dairy_peddler, cheese, apr)
    create_procurement_lifecycle(dairy_peddler, cheese, may)
    create_procurement_lifecycle(dairy_peddler, cheese, jun)

    create_procurement_lifecycle(beef_peddler, meat, jan)
    create_procurement_lifecycle(beef_peddler, meat, feb)
    create_procurement_lifecycle(beef_peddler, meat, mar)
    create_procurement_lifecycle(beef_peddler, meat, apr)
    create_procurement_lifecycle(beef_peddler, meat, may, do_pay=False)
    create_procurement_lifecycle(beef_peddler, meat, jun, do_pay=False)

    create_procurement_lifecycle(drink_peddler, drink, jan)
    create_procurement_lifecycle(drink_peddler, drink, feb, do_pay=False)
    create_procurement_lifecycle(drink_peddler, drink, mar, do_pay=False)
    create_procurement_lifecycle(drink_peddler, drink, apr, do_pay=False)
    create_procurement_lifecycle(drink_peddler, drink, may, do_pay=False)
    create_procurement_lifecycle(drink_peddler, drink, jun, do_pay=False)


def create_test_data():
    with db_transaction.atomic():
        create_default_chart_of_accounts()
        create_test_vendors()
        create_test_items()
        init_test_data()
        # create_test_customers()
        # create_test_customer_purchases()
