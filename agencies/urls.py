# agencies/urls.py
from django.urls import path
from . import views

app_name = 'agencies'
urlpatterns = [
    path('api/my-report/', views.AgencyReportAPIView.as_view(), name='agency_report_api'),
]
