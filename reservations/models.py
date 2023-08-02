import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

auth_user = get_user_model()


class Room(models.Model):
    name = models.CharField(max_length=20)
    price = models.IntegerField()

    def __str__(self):
        return self.name


class ReservationOptions(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")


class Reservation(models.Model):
    user = models.ForeignKey(auth_user, on_delete=models.CASCADE, null=True, blank=True)
    stay_type = models.CharField(max_length=255)
    stay_date_start = models.DateTimeField()
    stay_date_end = models.DateTimeField()
    reservation_options = models.ManyToManyField(ReservationOptions)
    updated_datetime = models.DateTimeField(auto_now=True)

    def get_reservation_range(self):
        return (
            self.stay_date_start.strftime("%Y-%m-%d %H:%S"),
            self.stay_date_end.strftime("%Y-%m-%d %H:%S"),
        )

    def __str__(self):
        start, end = self.get_reservation_range()
        return f"{start} to {end}"


class ReservedRoom(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    def __str__(self):
        start, end = self.reservation.get_reservation_range()
        return f"{self.room} reserved from {start} to {end}"


class PurchasedReservationOptions(models.Model):
    pass


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
