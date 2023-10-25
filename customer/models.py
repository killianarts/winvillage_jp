from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.translation import gettext_lazy as _
from faker import Faker
from phonenumber_field.modelfields import PhoneNumberField

auth_user = get_user_model()


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# Create your models here.
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
        company_name = (
            faker["en-US"]
            .company()
            .lower()
            .replace(" ", "")
            .replace(",", "")
            .replace("-", "")
        )
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

    user = models.OneToOneField(auth_user, on_delete=models.CASCADE, null=True)
    text = models.TextField()

    def __str__(self):
        return f"{self.text}, {self.created_at.strftime('%Y-%m-%d')}"


class Ticket(BaseModel):
    class Meta:
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    notes = models.ManyToManyField(TicketNote)
    is_resolved = models.BooleanField(default=False)

    def create_note(self, text):
        note = TicketNote.objects.create(text)
        note.save()
        self.notes.add(note)
        self.save()
        return note

    def update_note(self, note_id, text):
        note = TicketNote.objects.filter(ticket=self, id=note_id).first()
        if note.exists():
            note.text = text
            note.save()
            return note
        else:
            return None

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
