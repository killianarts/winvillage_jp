from django.contrib import admin
from reservations.models import (
    Reservation,
    Stay,
    OrderItem,
    Order,
)

admin.site.register(Reservation)
admin.site.register(Stay)
admin.site.register(Order)
admin.site.register(OrderItem)
