# core/signals.py
# version: 1.0.2
# REFACTOR: Updated wallet signal to react to status changes, not just creation.

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Wallet, WalletTransaction

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)

@receiver(post_save, sender=WalletTransaction)
def update_wallet_balance(sender, instance, **kwargs):
    """
    Signal handler to update the wallet's balance whenever a transaction's
    status is changed to 'completed' or a completed one is created.
    """
    # We check if the status is 'completed'. The calculation method already sums up only completed transactions.
    # This logic will correctly handle new transactions created as 'completed'
    # and existing transactions updated to 'completed'.
    wallet = instance.wallet
    new_balance = wallet.calculate_balance()
    
    # Update only if the balance has changed to avoid recursive signals
    if wallet.balance != new_balance:
        wallet.balance = new_balance
        wallet.save(update_fields=['balance'])
