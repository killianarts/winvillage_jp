from django.contrib import admin
from reservations.models import (
    Reservation,
    ReservationOption,
    Room,
    ReservedRoom,
    Stay,
    Grill,
    Food,
    ContactInfo,
)

admin.site.register(Reservation)
admin.site.register(ReservationOption)
admin.site.register(Room)
admin.site.register(ReservedRoom)
admin.site.register(Stay)
admin.site.register(Grill)
admin.site.register(Food)
admin.site.register(ContactInfo)
