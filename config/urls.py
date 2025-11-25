"""
URL configuration for blog-automation project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Health check endpoint (will be implemented in core app)
    # path('health/', include('apps.core.urls')),
    # path('', include('apps.core.urls')),  # Dashboard
    # path('accounts/', include('apps.accounts.urls')),
    # path('blog/', include('apps.blog.urls')),
    # path('api/', include('apps.blog.api_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
