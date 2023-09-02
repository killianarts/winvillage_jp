from django.contrib import admin
from core.models import Transaction, Item, ContactInfo, Category

admin.site.register(Transaction)
admin.site.register(Item)
admin.site.register(ContactInfo)
admin.site.register(Category)
