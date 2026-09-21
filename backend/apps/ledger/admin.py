from django.contrib import admin

from .models import Account, JournalEntry, JournalLine


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    readonly_fields = ["account", "debit", "credit"]
    can_delete = False


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "account_type", "business", "is_active"]
    list_filter = ["account_type", "is_active"]
    search_fields = ["code", "name"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ["entry_date", "description", "business", "source_type", "reverses"]
    list_filter = ["source_type"]
    search_fields = ["description", "source_id"]
    readonly_fields = [f.name for f in JournalEntry._meta.fields]
    inlines = [JournalLineInline]
