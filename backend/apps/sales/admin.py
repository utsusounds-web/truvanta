from django.contrib import admin
from .models import Sale, SaleItem, Payment, ReceiptPrintLog


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("transaction_number", "branch", "cashier", "status", "grand_total", "created_at")
    list_filter = ("status", "sale_type", "branch")
    inlines = [SaleItemInline, PaymentInline]


admin.site.register(ReceiptPrintLog)
