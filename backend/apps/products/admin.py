from django.contrib import admin
from .models import Category, Brand, UnitOfMeasure, Product, ProductUnit, ProductBatch, PriceHistory

admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(UnitOfMeasure)
admin.site.register(ProductUnit)
admin.site.register(ProductBatch)
admin.site.register(PriceHistory)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "barcode", "cost_price", "selling_price", "is_active", "business")
    search_fields = ("name", "sku", "barcode")
    list_filter = ("is_active", "business")
