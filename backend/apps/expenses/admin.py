from django.contrib import admin
from .models import ExpenseCategory, Expense, OwnerWithdrawal

admin.site.register(ExpenseCategory)
admin.site.register(Expense)
admin.site.register(OwnerWithdrawal)
