from django.contrib import admin
from reservations.models import Reservation, Room, ReservedRoom

admin.site.register(Reservation)
admin.site.register(Room)
admin.site.register(ReservedRoom)
