# -*- coding: utf-8 -*-
"""
Template view URL routing for accounts app
"""

from django.urls import path
from .views import login_view, logout_view, settings_view, supabase_login_view

app_name = 'accounts'

urlpatterns = [
    path('login/', login_view, name='login'),
    path('login/supabase/', supabase_login_view, name='supabase_login'),
    path('logout/', logout_view, name='logout'),
    path('settings/', settings_view, name='settings'),
]

