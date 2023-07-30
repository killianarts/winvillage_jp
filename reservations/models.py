from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils.translation import gettext_lazy as _
import uuid

auth_user = get_user_model()


class Room(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Reservation(models.Model):
    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True, blank=True)
    reserved_start_date = models.DateTimeField(default=timezone.now)
    reserved_end_date = models.DateTimeField()
    updated_datetime = models.DateTimeField(auto_now=True)

    def get_reservation_range(self):
        return self.reserved_start_date.strftime('%Y/%m/%d %H:%S'), self.reserved_end_date.strftime('%Y/%m/%d %H:%S')

    def __str__(self):
        start, end = self.get_reservation_range()
        return f"{start} to {end}"


class ReservedRoom(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        start, end = self.reservation.get_reservation_range()
        return f"{self.room} reserved from {start} to {end}"


# class Product(models.Model):
#     reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
#     amount = models.FloatField()
#     amount_field = models.CharField(max_length=150)
#     borrowed = models.BooleanField(default=False)
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#     object_id = models.PositiveIntegerField()
#     content_object = GenericForeignKey("content_type", "object_id")
#
#     @property
#     def available_amount(self):
#         return getattr(self.content_object, self.amount_field)
#
#     @property
#     def amount_without_this_product(self):
#         amount_now = self.available_amount
#         return amount_now - self.amount
#
#     def __str__(self):
#         return "%.2f ) %s" % (self.amount, self.content_object)


class ReservationToken(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    base_url = models.URLField(default="http://localhost:8000")
