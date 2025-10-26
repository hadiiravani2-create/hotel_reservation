# cancellations/admin.py
# version: 1.0.0
# FEATURE: Register CancellationPolicy and CancellationRule models with the Django admin.

from django.contrib import admin
from .models import CancellationPolicy, CancellationRule

class CancellationRuleInline(admin.TabularInline):
    """
    Allows editing CancellationRules directly within the CancellationPolicy admin page.
    Provides a more intuitive interface for managing rules associated with a policy.
    """
    model = CancellationRule
    extra = 1 # Show one empty form for adding a new rule by default
    fields = ('days_before_checkin_min', 'days_before_checkin_max', 'penalty_type', 'penalty_value')
    verbose_name = "قانون لغو"
    verbose_name_plural = "قوانین لغو جزئی"

@admin.register(CancellationPolicy)
class CancellationPolicyAdmin(admin.ModelAdmin):
    """
    Admin configuration for CancellationPolicy model.
    Includes an inline editor for associated CancellationRules.
    """
    list_display = ('name', 'description')
    search_fields = ('name',)
    inlines = [CancellationRuleInline] # Embed the rule editor within the policy page

# Optional: Register CancellationRule separately if direct access/editing is needed
# @admin.register(CancellationRule)
# class CancellationRuleAdmin(admin.ModelAdmin):
#     list_display = ('policy', 'days_before_checkin_min', 'days_before_checkin_max', 'penalty_type', 'penalty_value')
#     list_filter = ('policy', 'penalty_type')
#     search_fields = ('policy__name',)
