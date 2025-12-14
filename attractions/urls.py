# attractions/urls.py
# version: 1.0.0

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'attractions'

router = DefaultRouter()
router.register(r'list', views.AttractionViewSet, basename='attraction')

urlpatterns = [
    path('categories/', views.AttractionCategoryListView.as_view(), name='category-list'),
    path('', include(router.urls)),
]
