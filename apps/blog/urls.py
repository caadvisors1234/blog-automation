# -*- coding: utf-8 -*-
"""
URL routing for blog app

Includes both REST API endpoints and template view URLs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BlogPostViewSet, BlogImageViewSet, PostLogViewSet,
    post_list, post_create, post_detail, post_edit, post_delete, post_history,
    post_generating, post_select, post_select_confirm, post_regenerate,
)

app_name = 'blog'

# REST API router
router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='post-api')
router.register(r'images', BlogImageViewSet, basename='image-api')
router.register(r'logs', PostLogViewSet, basename='log-api')

# Template view patterns
template_urlpatterns = [
    path('posts/', post_list, name='post_list'),
    path('posts/create/', post_create, name='post_create'),
    path('posts/<int:pk>/', post_detail, name='post_detail'),
    path('posts/<int:pk>/edit/', post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', post_delete, name='post_delete'),
    path('posts/<int:pk>/generating/', post_generating, name='post_generating'),
    path('posts/<int:pk>/select/', post_select, name='post_select'),
    path('posts/<int:pk>/select/regenerate/', post_regenerate, name='post_regenerate'),
    path('posts/<int:pk>/select/confirm/', post_select_confirm, name='post_select_confirm'),
    path('history/', post_history, name='post_history'),
]

# Combine all patterns
urlpatterns = template_urlpatterns
