# attractions/views.py
# version: 2.0.0
# FEATURE: Updated filters to handle M2M relationships (categories, audiences).

from rest_framework import viewsets, generics
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Attraction, AttractionCategory
from .serializers import AttractionSerializer, AttractionCategorySerializer

class AttractionCategoryListView(generics.ListAPIView):
    """
    Returns a list of all attraction categories for filter menus.
    """
    queryset = AttractionCategory.objects.all()
    serializer_class = AttractionCategorySerializer
    permission_classes = [AllowAny]

class AttractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset to list and retrieve attractions.
    Supports filtering by City, Category, and Audience.
    """
    # Optimized query with prefetch_related for M2M fields
    queryset = Attraction.objects.select_related('city').prefetch_related(
        'categories', 'audiences', 'amenities', 'images'
    ).all()
    
    serializer_class = AttractionSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    
    # Filter fields updated for M2M relationships
    filterset_fields = {
        'city__slug': ['exact'],
        'categories__slug': ['exact', 'in'], # Can filter by multiple categories
        'audiences__name': ['exact'],
        'best_visit_time': ['exact'],
    }
    
    search_fields = ['name', 'description', 'city__name', 'amenities__name']
