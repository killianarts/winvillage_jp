from django.contrib import admin
from django.utils.html import format_html

from reservations.models import (
    Reservation,
    Stay,
    OrderItem,
    Order,
    Campaign,
    Room,
    PricingTier,
    PricingTierGroup,
    RoomTier,
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
        "room",
        "start",
        "end",
        "status_changed",
        "created_at",
        "updated_at",
    )


class PricingTierGroupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "display_tier_1",
        "display_tier_2",
        "display_tier_3",
        "display_tier_4",
        "display_tier_5",
        "display_tier_6",
    )

    def display_tier(self, obj, number_of_adults):
        # Retrieve PricingTier objects with the specified number_of_adults
        pricing_tier = obj.pricingtier_set.get(number_of_adults=number_of_adults)
        prices = f"Overnight: {pricing_tier.price_overnight}, Short-Term: {pricing_tier.price_short_term}"
        # Format the output as a string, for example, listing the names of the PricingTier objects
        return prices

    def display_tier_1(self, obj):
        return self.display_tier(obj, 1)

    display_tier_1.short_description = "1 adult"

    def display_tier_2(self, obj):
        return self.display_tier(obj, 2)

    display_tier_2.short_description = "2 adults"

    def display_tier_3(self, obj):
        return self.display_tier(obj, 3)

    display_tier_3.short_description = "3 adults"

    def display_tier_4(self, obj):
        return self.display_tier(obj, 4)

    display_tier_4.short_description = "4 adults"

    def display_tier_5(self, obj):
        return self.display_tier(obj, 5)

    display_tier_5.short_description = "5 adults"

    def display_tier_6(self, obj):
        return self.display_tier(obj, 6)

    display_tier_6.short_description = "6 adults"


admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Stay, StayAdmin)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Campaign)
admin.site.register(Room)
admin.site.register(RoomTier)
admin.site.register(PricingTier)
admin.site.register(PricingTierGroup, PricingTierGroupAdmin)
