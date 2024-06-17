from django.core.management.base import BaseCommand
from django.conf import settings
from hordak.models import Account
from core.accounting_utils import create_default_chart_of_accounts
from django.utils.translation import gettext_lazy as _


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            accounts = create_default_chart_of_accounts
            print("============================")
            print(
                _(
                    "A default chart of accounts has been created if it didn't already exist."
                )
            )
            print("============================")
        except Exception as e:
            print(f"There was an error: {e}")
