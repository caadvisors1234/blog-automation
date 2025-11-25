# -*- coding: utf-8 -*-
"""
REST API URL routing for blog app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet, BlogImageViewSet, PostLogViewSet

app_name = 'blog_api'

# REST API router
router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='post')
router.register(r'images', BlogImageViewSet, basename='image')
router.register(r'logs', PostLogViewSet, basename='log')

urlpatterns = [
    path('', include(router.urls)),
]

