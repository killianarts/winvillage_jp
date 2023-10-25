from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            u = None
            if (
                not User.objects.filter(email=settings.DJANGO_SUPER_USER_EMAIL).exists()
                and not User.objects.filter(is_superuser=True).exists()
            ):
                print("admin user not found, creating one")
                name = settings.DJANGO_SUPER_USER_NAME
                email = settings.DJANGO_SUPER_USER_EMAIL
                new_password = None
                if not settings.DJANGO_SUPER_USER_PASSWORD:
                    new_password = get_random_string(10)
                else:
                    new_password = settings.DJANGO_SUPER_USER_PASSWORD

                u = User.objects.create_superuser(email, new_password, name=name)
                print("===================================")
                print(
                    f"A superuser was created with name {name} email {email} and password {new_password}"
                )
                print("===================================")
            else:
                print("admin user found. Skipping super user creation")
            print(u)
        except Exception as e:
            print(f"There was an error: {e}")
