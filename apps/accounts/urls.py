# -*- coding: utf-8 -*-
"""
URL routing for accounts app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, SALONBoardAccountViewSet

app_name = 'accounts'

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'salon-board-accounts', SALONBoardAccountViewSet, basename='salon-board-account')

urlpatterns = [
    path('', include(router.urls)),
]
