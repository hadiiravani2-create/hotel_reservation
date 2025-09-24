# agencies/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.AgencyUserManagementViewSet, basename='agency-user')
router.register(r'roles', views.AgencyUserRoleViewSet, basename='agency-user-role')

app_name = 'agencies'
urlpatterns = [
    path('api/', include(router.urls)),
    path('api/my-report/', views.AgencyReportAPIView.as_view(), name='agency_report_api'),
]
