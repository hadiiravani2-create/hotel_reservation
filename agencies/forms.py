# agencies/forms.py

from django import forms
from django_jalali.forms import jDateField
from .models import Contract, AgencyTransaction
from jalali_date.widgets import AdminJalaliDateWidget

class ContractForm(forms.ModelForm):
    start_date = jDateField(label="تاریخ شروع قرارداد", widget=AdminJalaliDateWidget)
    end_date = jDateField(label="تاریخ پایان قرارداد", widget=AdminJalaliDateWidget)

    class Meta:
        model = Contract
        fields = '__all__'

class AgencyTransactionForm(forms.ModelForm):
    transaction_date = jDateField(label="تاریخ تراکنش", widget=AdminJalaliDateWidget)

    class Meta:
        model = AgencyTransaction
        fields = '__all__'