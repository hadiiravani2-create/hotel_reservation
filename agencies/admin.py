# agencies/admin.py

from django.contrib import admin
from .models import Agency, AgencyTransaction, Contract

class AgencyTransactionInline(admin.TabularInline):
    model = AgencyTransaction
    extra = 0
    readonly_fields = ('booking', 'amount', 'transaction_type', 'description', 'created_at', 'created_by')

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone_number', 'credit_limit', 'current_balance')
    search_fields = ('name', 'contact_person')
    readonly_fields = ('current_balance',)
    inlines = [AgencyTransactionInline]

@admin.register(AgencyTransaction)
class AgencyTransactionAdmin(admin.ModelAdmin):
    list_display = ('agency', 'transaction_type', 'amount', 'booking', 'created_at', 'created_by')
    list_filter = ('agency', 'transaction_type', 'created_at')

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('agency', 'hotel', 'start_date', 'end_date', 'contract_type')
    list_filter = ('agency', 'hotel', 'contract_type')
    filter_horizontal = ('credit_blacklist_hotels',) # ویجت بهتر برای انتخاب چندتایی