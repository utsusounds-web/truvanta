from django.contrib import admin
from .models import Customer, CustomerCreditTransaction

admin.site.register(Customer)
admin.site.register(CustomerCreditTransaction)
