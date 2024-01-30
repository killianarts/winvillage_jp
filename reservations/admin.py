from django.contrib import admin
from reservations.models import (
    Reservation,
    Stay,
    OrderItem,
    Order,
    SpecialDate,
)


class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "stay",
        "first_name",
        "last_name",
        "email",
        "phone",
        "order_items_list",
    )


class StayAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "start",
        "end",
        "status_changed",
        "type_changed",
        "created_at",
        "updated_at",
    )


admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Stay, StayAdmin)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(SpecialDate)
