# agencies/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Sum
from .models import AgencyTransaction, Agency

@receiver(post_save, sender=AgencyTransaction)
def update_agency_balance(sender, instance, **kwargs):
    """
    پس از ذخیره هر تراکنش، بدهی کل آژانس را دوباره محاسبه و ذخیره می‌کند.
    """
    agency = instance.agency
    total_balance = AgencyTransaction.objects.filter(agency=agency).aggregate(total=Sum('amount'))['total'] or 0
    agency.current_balance = total_balance
    agency.save(update_fields=['current_balance'])