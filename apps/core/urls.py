"""
Core URL configuration for health checks and essential endpoints.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Health checks
    path('health/', views.health_check, name='health_check'),
    path('ready/', views.readiness_check, name='readiness_check'),
    path('live/', views.liveness_check, name='liveness_check'),
]

