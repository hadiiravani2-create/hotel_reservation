# cancellations/urls.py
# version: 1.0.0
# FEATURE: Initial URL configuration for cancellation policies and rules.

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'cancellations'

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'policies', views.CancellationPolicyViewSet, basename='cancellation-policy')
router.register(r'rules', views.CancellationRuleViewSet, basename='cancellation-rule')

# The API URLs are automatically determined by the router.
urlpatterns = [
    path('', include(router.urls)),
]
