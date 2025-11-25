"""
Core views for the blog-automation application.

This module provides essential views for application health monitoring
and basic functionality.
"""

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
import redis
import os


@login_required
def dashboard(request):
    """
    Dashboard view showing statistics and recent posts.
    """
    from apps.blog.models import BlogPost, PostLog
    
    user = request.user
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get statistics
    posts = BlogPost.objects.filter(user=user)
    total_posts = posts.count()
    monthly_posts = posts.filter(created_at__gte=month_start).count()
    published_posts = posts.filter(status='published').count()
    success_rate = round((published_posts / total_posts * 100) if total_posts > 0 else 0)
    
    # Status counts
    status_counts = {
        'draft': posts.filter(status='draft').count(),
        'generating': posts.filter(status='generating').count(),
        'ready': posts.filter(status='ready').count(),
        'publishing': posts.filter(status='publishing').count(),
        'published': published_posts,
        'failed': posts.filter(status='failed').count(),
    }
    
    # Recent posts
    recent_posts = posts.order_by('-created_at')[:5]
    
    # Recent logs
    recent_logs = PostLog.objects.filter(user=user).order_by('-started_at')[:10]
    
    context = {
        'total_posts': total_posts,
        'monthly_posts': monthly_posts,
        'success_rate': success_rate,
        'published_posts': published_posts,
        'status_counts': status_counts,
        'recent_posts': recent_posts,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'dashboard.html', context)


def health_check(request):
    """
    Health check endpoint for Docker and load balancer health monitoring.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Basic application status
    
    Returns:
        JsonResponse with health status and component details
    """
    health_status = {
        'status': 'healthy',
        'components': {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health_status['components']['database'] = 'ok'
    except Exception as e:
        health_status['components']['database'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Check Redis
    try:
        redis_host = os.environ.get('REDIS_HOST', 'redis')
        redis_client = redis.Redis(host=redis_host, port=6379, socket_timeout=2)
        redis_client.ping()
        health_status['components']['redis'] = 'ok'
    except Exception as e:
        health_status['components']['redis'] = f'error: {str(e)}'
        health_status['status'] = 'unhealthy'
    
    # Determine HTTP status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    
    return JsonResponse(health_status, status=status_code)


def readiness_check(request):
    """
    Readiness check endpoint for Kubernetes/orchestration systems.
    
    Simpler check that verifies the application is ready to receive traffic.
    
    Returns:
        JsonResponse with readiness status
    """
    return JsonResponse({'status': 'ready'})


def liveness_check(request):
    """
    Liveness check endpoint for Kubernetes/orchestration systems.
    
    Verifies the application process is alive and responsive.
    
    Returns:
        JsonResponse with liveness status
    """
    return JsonResponse({'status': 'alive'})

