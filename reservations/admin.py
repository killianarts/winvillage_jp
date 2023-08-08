from django.contrib import admin
from reservations.models import (
    Reservation,
    Room,
    Stay,
    ContactInfo,
    Item,
    OrderItem,
    Category,
    Order,
)

admin.site.register(Reservation)
admin.site.register(Room)
admin.site.register(Stay)
admin.site.register(ContactInfo)
admin.site.register(Item)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Category)
