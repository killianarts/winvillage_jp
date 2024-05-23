import datetime
from collections import OrderedDict

import pendulum
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from faker import Faker
from phonenumber_field.modelfields import PhoneNumberField


auth_user = get_user_model()


class PendulumDateTimeField(models.DateTimeField):
    # https://docs.djangoproject.com/en/5.0/howto/custom-model-fields#converting-values-to-python-objects
    # If present for the field subclass, from_db_value() will be called in all circumstances when
    # the data is loaded from the database, including in aggregates and values() calls.
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        return pendulum.parse(value)

    # https://docs.djangoproject.com/en/5.0/howto/custom-model-fields#converting-values-to-python-objects
    # to_python() is called by deserialization and during the clean() method used from forms.

    # As a general rule, to_python() should deal gracefully with any of the following arguments:
    # -- An instance of the correct type
    # -- A string
    # -- None (if the field allows null=True)
    def to_python(self, value):
        if isinstance(value, pendulum.DateTime):
            return value
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        if value is None:
            return value
        return pendulum.parse(value)

    def get_prep_value(self, value):
        if isinstance(value, pendulum.DateTime):
            return value.to_iso8601_string()
        if isinstance(value, datetime.datetime):
            return pendulum.instance(value)
        if isinstance(value, datetime.date):
            return pendulum.instance(value)
        if value is None:
            return value


class BaseModel(models.Model):
    created_at = PendulumDateTimeField(auto_now_add=True, null=True)
    updated_at = PendulumDateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class Customer(BaseModel):
    class Meta:
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")

    user = models.OneToOneField(auth_user, on_delete=models.CASCADE, null=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = PhoneNumberField()
    email = models.EmailField(max_length=254)

    def __str__(self):
        return f"{self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


def make_customers(count):
    locales = OrderedDict(
        [
            ("en-US", 1),
            ("ja_JP", 2),
        ]
    )
    faker = Faker(locales)
    created = []
    for i in range(count):
        first_name = faker["ja-JP"].first_name()
        last_name = faker["ja-JP"].last_name()
        company_name = faker["en-US"].company().lower().replace(" ", "").replace(",", "").replace("-", "")
        email = f"{last_name.lower()}{first_name.lower()}@{company_name}.com"
        phone = faker["ja-JP"].phone_number()
        created.append(
            Customer.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
            )
        )
    return created


class TicketNote(BaseModel):
    class Meta:
        verbose_name = _("Ticket Note")
        verbose_name_plural = _("Ticket Notes")

    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True)
    text = models.TextField(null=False, blank=False)

    def __str__(self):
        return f"{self.text}, {self.created_at.strftime('%Y-%m-%d')}"


class Ticket(BaseModel):
    class Meta:
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    notes = models.ManyToManyField(TicketNote)
    is_closed = models.BooleanField(default=False)

    def add_note(self, user, data):
        ticket_note = TicketNote.objects.create(user=user, text=data["notes"])
        ticket_note.save()
        self.customer.first_name = data["first_name"]
        self.customer.last_name = data["last_name"]
        self.customer.email = data["email"]
        self.customer.phone = data["phone"]
        self.customer.save()
        self.notes.add(ticket_note)
        self.save()

    def update_note(self, note_id, text):
        note = TicketNote.objects.filter(ticket=self, id=note_id).first()
        if note.exists():
            note.text = text
            note.save()
            return note
        else:
            return None

    def close_ticket(self, user, data):
        ticket_note = TicketNote.objects.create(user=user, text=data["notes"])
        ticket_note.save()
        self.customer.first_name = data["first_name"]
        self.customer.last_name = data["last_name"]
        self.customer.email = data["email"]
        self.customer.phone = data["phone"]
        self.customer.save()
        self.notes.add(ticket_note)
        self.is_closed = True
        self.save()

    def reopen_ticket(self, user, data):
        ticket_note = TicketNote.objects.create(user=user, text=data["notes"])
        ticket_note.save()
        self.customer.first_name = data["first_name"]
        self.customer.last_name = data["last_name"]
        self.customer.email = data["email"]
        self.customer.phone = data["phone"]
        self.customer.save()
        self.notes.add(ticket_note)
        self.is_closed = False
        self.save()

    def delete_note(self, note_id):
        note = TicketNote.objects.filter(ticket=self, id=note_id).first()
        if note.exists():
            note.delete()
        else:
            raise ObjectDoesNotExist

    @property
    def all_notes(self):
        notes = TicketNote.objects.filter(ticket=self).order_by("created_at")
        return notes

    def __str__(self):
        return f"{self.customer}, {self.created_at}"
