from django.contrib import admin
from customer.models import Customer, Ticket, TicketNote

# Register your models here.

admin.site.register(Customer)
admin.site.register(Ticket)
admin.site.register(TicketNote)
