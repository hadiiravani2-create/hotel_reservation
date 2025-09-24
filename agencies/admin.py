# agencies/admin.py

from django.contrib import admin
from .models import Agency, AgencyTransaction, Contract, StaticRate
from .forms import ContractForm, AgencyTransactionForm

class AgencyTransactionInline(admin.TabularInline):
    model = AgencyTransaction
    form = AgencyTransactionForm
    extra = 0
    readonly_fields = ('booking', 'amount', 'transaction_type', 'description', 'created_at', 'created_by')

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone_number', 'credit_limit', 'current_balance', 'default_discount_percentage')
    search_fields = ('name', 'contact_person')
    readonly_fields = ('current_balance',)
    inlines = [AgencyTransactionInline]
    filter_horizontal = ('credit_blacklist_hotels',)
@admin.register(AgencyTransaction)
class AgencyTransactionAdmin(admin.ModelAdmin):
    form = AgencyTransactionForm
    list_display = ('agency', 'transaction_type', 'amount', 'transaction_date', 'booking', 'tracking_code', 'created_by')
    list_filter = ('agency', 'transaction_type', 'transaction_date')
    search_fields = ('tracking_code', 'agency__name', 'description')

class StaticRateInline(admin.TabularInline):
    model = StaticRate
    extra = 1
    # برای محدود کردن لیست اتاق‌ها به هتل انتخاب شده، نیاز به جاوا اسکریپت سفارشی است که در آینده اضافه می‌کنیم

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    form = ContractForm
    list_display = ('title', 'agency', 'hotel', 'start_date', 'end_date', 'contract_type')
    list_filter = ('agency', 'hotel', 'contract_type')
    inlines = [StaticRateInline]
