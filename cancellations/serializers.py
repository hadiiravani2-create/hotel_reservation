# cancellations/serializers.py
# version: 1.0.0
# FEATURE: Initial serializers for CancellationPolicy and CancellationRule.

from rest_framework import serializers
from .models import CancellationPolicy, CancellationRule

class CancellationRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for the detailed cancellation rules.
    """
    class Meta:
        model = CancellationRule
        fields = [
            'id', 
            'days_before_checkin_min', 
            'days_before_checkin_max', 
            'penalty_type', 
            'penalty_value'
        ]

class CancellationPolicySerializer(serializers.ModelSerializer):
    """
    Serializer for the main cancellation policy.
    Includes nested rules for detailed display.
    """
    # Define nested serializer for rules (read-only when fetching a policy)
    rules = CancellationRuleSerializer(many=True, read_only=True)

    class Meta:
        model = CancellationPolicy
        fields = ['id', 'name', 'description', 'rules']
