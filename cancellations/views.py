# cancellations/views.py
# version: 1.0.0
# FEATURE: Initial ViewSets for CancellationPolicy and CancellationRule.

from rest_framework import viewsets
from .models import CancellationPolicy, CancellationRule
from .serializers import CancellationPolicySerializer, CancellationRuleSerializer

class CancellationPolicyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cancellation Policies to be viewed or edited.
    Provides full CRUD operations for policies.
    """
    queryset = CancellationPolicy.objects.all()
    serializer_class = CancellationPolicySerializer
    # Add permissions later, e.g., [IsAdminUser]

class CancellationRuleViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Cancellation Rules to be viewed or edited.
    Provides full CRUD operations for individual rules within policies.
    """
    queryset = CancellationRule.objects.all()
    serializer_class = CancellationRuleSerializer
    # Add permissions later, e.g., [IsAdminUser]
