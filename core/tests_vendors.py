from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.test import Client, TestCase
from freezegun import freeze_time
from hordak.models import Account
from phonenumber_field.phonenumber import PhoneNumber

from core.accounting_utils import create_default_chart_of_accounts
from core.models import Vendor

User = get_user_model()


class VendorAndAccountViewTests(TestCase):
    def setUp(self):
        create_default_chart_of_accounts()
        superuser = User.objects.create_superuser(
            email="micah@killianarts.online", password="m1j0k1j0"
        )

    def test_vendor_create_GET(self):
        c = Client()
        c.login(email="micah@killianarts.online", password="m1j0k1j0")
        print(c.get("/winadmin/vendor/create/"))
        print("==========Vendor Create GET==========")
        assert c.get("/winadmin/vendor/create/")
        print("====================")
        print("")

    def test_vendor_create_POST(self):
        c = Client()
        c.login(email="micah@killianarts.online", password="m1j0k1j0")
        print("==========Vendor Create POST==========")
        print(
            c.post(
                "/winadmin/vendor/create/",
                {
                    "name": "Tender Cow Parts",
                    "cutoff_day": 30,
                    "due_day": 30,
                    "phone": PhoneNumber.from_string("+8107043327278", region="JA"),
                    "address": "Jonai",
                    "postal_code": "8400041",
                    "city": "Saga",
                    "prefecture": "Saga",
                },
            )
        )
        assert Vendor.objects.get(name="Tender Cow Parts")
        print("====================")
        print("")
