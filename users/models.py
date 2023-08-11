from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db import models


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.

    Taken from: https://testdriven.io/blog/django-custom-user-model/
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        :param email:
        :param password:
        :param extra_fields:
        :return:
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


# class User(AbstractUser):
#     """
#     Default custom user model for win_village.
#     If adding fields that need to be filled at user signup,
#     check forms.SignupForm and forms.SocialSignupForms accordingly.
#     """
#
#     # First and last name do not cover name patterns around the globe
#     name = CharField(_("Name of User"), blank=True, max_length=255)
#     first_name = None  # type: ignore
#     last_name = None  # type: ignore
#
#     def get_absolute_url(self) -> str:
#         """Get URL for user's detail view.
#
#         Returns:
#             str: URL for user detail.
#
#         """
#         return reverse("users:detail", kwargs={"username": self.username})


class User(AbstractUser):
    """
    Default custom user model for win_village.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


# class Account(AbstractUser):
#     username = None
#     email = models.EmailField(_("email address"), unique=True)
#     USERNAME_FIELD = "email"
#     REQUIRED_FIELDS = []
#
#     objects = AccountManager()
#
#     def __str__(self):
#         return self.email
