from django.contrib import admin

from core.models import (
    Category,
    ContactInfo,
    Invoice,
    Item,
    Procurement,
    Transaction,
    Vendor,
)


class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price_per_unit",
        "quantity",
        "total_price",
        "created_at",
        "updated_at",
    )


admin.site.register(Transaction, TransactionAdmin)


class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "stock_quantity",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return Item.objects.all()


admin.site.register(Item, ItemAdmin)
admin.site.register(ContactInfo)
admin.site.register(Category)
admin.site.register(Vendor)
admin.site.register(Procurement)
admin.site.register(Invoice)
