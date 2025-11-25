# -*- coding: utf-8 -*-
"""
URL routing for blog app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet

app_name = 'blog'

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='post')

urlpatterns = [
    path('', include(router.urls)),
]
