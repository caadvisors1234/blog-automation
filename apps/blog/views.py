# -*- coding: utf-8 -*-
"""
Blog post management views
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action

logger = logging.getLogger(__name__)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import models
from django.db.models import Q
from django.utils import timezone
from .models import BlogPost, BlogImage, PostLog
from .serializers import (
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostCreateSerializer,
    BlogPostUpdateSerializer,
    BlogImageSerializer,
    PostLogSerializer,
    MAX_IMAGES_PER_POST,
)


class BlogPostViewSet(viewsets.ModelViewSet):
    """
    Blog post management viewset

    Provides endpoints for:
    - GET /api/blog/posts/ - List user's blog posts
    - POST /api/blog/posts/ - Create new blog post
    - GET /api/blog/posts/{id}/ - Get specific post
    - PATCH /api/blog/posts/{id}/ - Update post
    - DELETE /api/blog/posts/{id}/ - Delete post
    - POST /api/blog/posts/{id}/generate/ - Trigger AI generation
    - POST /api/blog/posts/{id}/publish/ - Trigger SALON BOARD publishing
    - GET /api/blog/posts/{id}/images/ - List post images
    - POST /api/blog/posts/{id}/images/ - Add image to post
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """
        Get blog posts for current user

        Returns:
            QuerySet of user's blog posts
        """
        queryset = BlogPost.objects.filter(user=self.request.user)

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by AI-generated
        ai_generated = self.request.query_params.get('ai_generated')
        if ai_generated is not None:
            ai_generated_bool = ai_generated.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(ai_generated=ai_generated_bool)

        # Search by title or content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )

        return queryset.select_related('user').prefetch_related('images').order_by('-created_at')

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action

        Returns:
            Serializer class
        """
        if self.action == 'list':
            return BlogPostListSerializer
        elif self.action == 'create':
            return BlogPostCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return BlogPostUpdateSerializer
        else:
            return BlogPostDetailSerializer

    def perform_create(self, serializer):
        """
        Create blog post for current user

        Args:
            serializer: Validated serializer instance
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='generate')
    def generate(self, request, pk=None):
        """
        Trigger AI content generation for blog post

        Args:
            request: HTTP request
            pk: Blog post ID

        Returns:
            Response with task information
        """
        blog_post = self.get_object()

        # Validate that post can be generated
        if blog_post.status != 'draft':
            return Response(
                {'detail': 'Post must be in draft status to generate'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not blog_post.ai_prompt and not blog_post.keywords:
            return Response(
                {'detail': 'AI prompt or keywords are required for generation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to generating
        blog_post.status = 'generating'
        blog_post.save(update_fields=['status'])

        # Import here to avoid circular imports
        from .tasks import generate_blog_content_task

        # Trigger Celery task
        task = generate_blog_content_task.delay(blog_post.id)

        # Save task ID
        blog_post.celery_task_id = task.id
        blog_post.save(update_fields=['celery_task_id'])

        return Response({
            'detail': 'AI content generation started',
            'task_id': task.id,
            'post_id': blog_post.id,
            'status': blog_post.status,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """
        Trigger SALON BOARD publishing for blog post

        Args:
            request: HTTP request
            pk: Blog post ID

        Returns:
            Response with task information
        """
        blog_post = self.get_object()

        # Validate that post can be published
        if blog_post.status not in ['ready', 'failed']:
            return Response(
                {'detail': 'Post must be in ready or failed status to publish'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not blog_post.title or not blog_post.content:
            return Response(
                {'detail': 'Title and content are required for publishing'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user has SALON BOARD account
        if not hasattr(request.user, 'salon_board_account'):
            return Response(
                {'detail': 'SALON BOARD account is required for publishing'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.salon_board_account.is_active:
            return Response(
                {'detail': 'SALON BOARD account is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status to publishing
        blog_post.status = 'publishing'
        blog_post.save(update_fields=['status'])

        # Delete existing PostLog if exists (OneToOneField constraint)
        try:
            existing_log = PostLog.objects.get(blog_post=blog_post)
            existing_log.delete()
            logger.info(f"Deleted existing PostLog for blog_post {blog_post.id}")
        except PostLog.DoesNotExist:
            pass

        # Create new PostLog
        post_log = PostLog.objects.create(
            user=request.user,
            blog_post=blog_post,
            status='in_progress',
            started_at=timezone.now()
        )

        # Import here to avoid circular imports
        from .tasks import publish_to_salon_board_task

        # Trigger Celery task
        task = publish_to_salon_board_task.delay(blog_post.id, post_log.id)

        # Save task ID
        blog_post.celery_task_id = task.id
        blog_post.save(update_fields=['celery_task_id'])

        return Response({
            'detail': 'SALON BOARD publishing started',
            'task_id': task.id,
            'post_id': blog_post.id,
            'log_id': post_log.id,
            'status': blog_post.status,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        Get statistics for user's blog posts

        Args:
            request: HTTP request

        Returns:
            Response with statistics data
        """
        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        
        user_posts = BlogPost.objects.filter(user=request.user)
        
        # Total counts
        total = user_posts.count()
        
        # Status counts
        status_counts = dict(user_posts.values_list('status').annotate(count=Count('id')))
        
        # This month's posts
        this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = user_posts.filter(created_at__gte=this_month_start).count()
        
        # Success rate (published / (published + failed))
        published = status_counts.get('published', 0)
        failed = status_counts.get('failed', 0)
        success_rate = round((published / (published + failed) * 100)) if (published + failed) > 0 else 0
        
        return Response({
            'total': total,
            'this_month': this_month,
            'success_rate': success_rate,
            'draft': status_counts.get('draft', 0),
            'generating': status_counts.get('generating', 0),
            'ready': status_counts.get('ready', 0),
            'publishing': status_counts.get('publishing', 0),
            'published': published,
            'failed': failed,
        })

    @action(detail=True, methods=['get', 'post'], url_path='images')
    def images(self, request, pk=None):
        """
        List or add images to blog post

        Args:
            request: HTTP request
            pk: Blog post ID

        Returns:
            Response with images or created image
        """
        blog_post = self.get_object()

        if request.method == 'GET':
            images = blog_post.images.all()
            serializer = BlogImageSerializer(images, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            # Check image count limit
            if blog_post.images.count() >= MAX_IMAGES_PER_POST:
                return Response(
                    {'detail': f'Maximum {MAX_IMAGES_PER_POST} images allowed per post'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            image_file = request.FILES.get('image')
            if not image_file:
                return Response(
                    {'detail': 'Image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine order
            max_order = blog_post.images.aggregate(
                max_order=models.Max('order')
            )['max_order']
            next_order = (max_order or -1) + 1

            image = BlogImage.objects.create(
                blog_post=blog_post,
                image_file=image_file,
                order=next_order
            )

            serializer = BlogImageSerializer(image)
            return Response(serializer.data, status=status.HTTP_201_CREATED)


class BlogImageViewSet(viewsets.ModelViewSet):
    """
    Blog image management viewset

    Provides endpoints for:
    - GET /api/blog/images/{id}/ - Get specific image
    - PATCH /api/blog/images/{id}/ - Update image (order)
    - DELETE /api/blog/images/{id}/ - Delete image
    """
    serializer_class = BlogImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get images for current user's posts

        Returns:
            QuerySet of user's blog images
        """
        return BlogImage.objects.filter(
            blog_post__user=self.request.user
        ).select_related('blog_post')


class PostLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Post log viewset (read-only)

    Provides endpoints for:
    - GET /api/blog/logs/ - List user's post logs
    - GET /api/blog/logs/{id}/ - Get specific log
    """
    serializer_class = PostLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Get post logs for current user

        Returns:
            QuerySet of user's post logs
        """
        queryset = PostLog.objects.filter(user=self.request.user)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('blog_post', 'user').order_by('-started_at')


# ========================================
# Template Views (Frontend)
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse


@login_required
def post_list(request):
    """
    Blog post list view.
    """
    posts = BlogPost.objects.filter(user=request.user).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        posts = posts.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(keywords__icontains=search)
        )
    
    context = {
        'posts': posts,
        'status_filter': status_filter,
        'search': search,
        'status_choices': BlogPost.STATUS_CHOICES,
    }
    
    return render(request, 'blog/list.html', context)


@login_required
def post_create(request):
    """
    Blog post creation view.
    Creates post and immediately starts AI generation (3 variations).
    """
    from .hpb_scraper import scrape_stylists, scrape_coupons
    from .tasks import generate_blog_content_task
    
    # Get user's salon info for stylists and coupons
    stylists = []
    coupons = []
    
    if request.user.hpb_salon_url:
        try:
            stylists = scrape_stylists(request.user.hpb_salon_url)
        except Exception as e:
            messages.warning(request, f'スタイリスト情報の取得に失敗しました: {str(e)}')
        
        try:
            coupons = scrape_coupons(request.user.hpb_salon_url)
        except Exception as e:
            messages.warning(request, f'クーポン情報の取得に失敗しました: {str(e)}')
    
    if request.method == 'POST':
        # Handle form submission
        keywords = (request.POST.get('keywords') or '').strip()
        ai_prompt = (request.POST.get('ai_prompt') or '').strip()
        tone = request.POST.get('tone', 'friendly')
        stylist_id = request.POST.get('stylist_id', '')
        coupon_name = request.POST.get('coupon_name', '')

        if not keywords:
            messages.error(request, 'キーワードは必須です。')
            return redirect('blog:post_create')
        
        # Create post with 'generating' status (skip draft)
        post = BlogPost.objects.create(
            user=request.user,
            title='',  # AI will generate
            ai_prompt=ai_prompt,  # Optional: user can provide custom instructions
            keywords=keywords,
            tone=tone,
            stylist_id=stylist_id,
            coupon_name=coupon_name,
            status='generating',  # Start with generating status
        )
        
        # Handle image uploads
        images = request.FILES.getlist('images')
        logger.info(f"Received {len(images)} images for post {post.id}")
        logger.info(f"request.FILES keys: {list(request.FILES.keys())}")
        for i, image in enumerate(images[:MAX_IMAGES_PER_POST]):
            logger.info(f"Saving image {i+1}: {image.name}, size={image.size}")
            BlogImage.objects.create(
                blog_post=post,
                image_file=image,
                order=i + 1,
            )
        
        # Immediately start AI generation task
        task = generate_blog_content_task.delay(post.id)
        post.celery_task_id = task.id
        post.save(update_fields=['celery_task_id'])
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('blog:post_generating', kwargs={'pk': post.pk}),
                'post_id': post.id,
                'image_count': post.images.count(),
            })
        
        messages.info(request, 'AIが3つの記事案を生成中です。少々お待ちください...')
        return redirect('blog:post_generating', pk=post.pk)
    
    context = {
        'stylists': stylists,
        'coupons': coupons,
        'tone_choices': [
            ('friendly', 'フレンドリー'),
            ('professional', 'プロフェッショナル'),
            ('casual', 'カジュアル'),
            ('formal', 'フォーマル'),
        ],
    }
    
    return render(request, 'blog/create.html', context)


@login_required
def post_generating(request, pk):
    """
    AI generation waiting view.
    Shows progress while AI generates 3 article variations.
    """
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    
    # If already done generating, redirect to select or detail
    if post.status == 'selecting':
        return redirect('blog:post_select', pk=post.pk)
    elif post.status in ['ready', 'published']:
        return redirect('blog:post_detail', pk=post.pk)
    elif post.status == 'failed':
        messages.error(request, 'AI記事生成に失敗しました。再度お試しください。')
        return redirect('blog:post_detail', pk=post.pk)
    
    context = {
        'post': post,
    }
    
    return render(request, 'blog/generating.html', context)


@login_required
def post_select(request, pk):
    """
    Article selection view.
    Displays 3 AI-generated variations for user to choose from.
    """
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    
    # Redirect if not in selecting status
    if post.status != 'selecting':
        if post.status == 'generating':
            return redirect('blog:post_generating', pk=post.pk)
        return redirect('blog:post_detail', pk=post.pk)
    
    # Get variations
    variations = post.generated_variations or []
    
    if not variations:
        messages.error(request, '生成された記事がありません。再度お試しください。')
        return redirect('blog:post_detail', pk=post.pk)
    
    # Get images for preview
    images = post.images.all().order_by('order')
    
    context = {
        'post': post,
        'variations': variations,
        'images': images,
    }
    
    return render(request, 'blog/select_article.html', context)


@login_required
def post_select_confirm(request, pk):
    """
    Confirm article selection.
    Saves the selected variation as the final article.
    """
    if request.method != 'POST':
        return redirect('blog:post_select', pk=pk)
    
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    
    # Validate status
    if post.status != 'selecting':
        messages.error(request, '記事の選択ができない状態です。')
        return redirect('blog:post_detail', pk=post.pk)
    
    # Get selected variation ID
    try:
        selected_id = int(request.POST.get('variation_id', 0))
    except (TypeError, ValueError):
        messages.error(request, '不正な選択です。')
        return redirect('blog:post_select', pk=post.pk)
    
    # Find selected variation
    variations = post.generated_variations or []
    selected_variation = None
    
    for var in variations:
        if var.get('id') == selected_id:
            selected_variation = var
            break
    
    if not selected_variation:
        messages.error(request, '選択された記事が見つかりません。')
        return redirect('blog:post_select', pk=post.pk)
    
    # Save selected variation as the final article
    post.title = selected_variation.get('title', '')[:25]
    post.content = selected_variation.get('content', '')
    post.generated_content = selected_variation.get('content', '')  # Backup
    post.status = 'ready'
    post.save(update_fields=['title', 'content', 'generated_content', 'status'])
    
    messages.success(request, f'記事「{post.title}」を選択しました。投稿準備が完了しました。')
    return redirect('blog:post_detail', pk=post.pk)


@login_required
def post_detail(request, pk):
    """
    Blog post detail view.
    """
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    images = post.images.all().order_by('order')
    logs = PostLog.objects.filter(blog_post=post).order_by('-started_at')[:10]
    
    context = {
        'post': post,
        'images': images,
        'logs': logs,
    }
    
    return render(request, 'blog/detail.html', context)


@login_required
def post_edit(request, pk):
    """
    Blog post edit view.
    """
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Update post
        post.title = request.POST.get('title', post.title)[:25]
        post.content = request.POST.get('content', post.content)
        post.ai_prompt = request.POST.get('ai_prompt', post.ai_prompt)
        post.keywords = request.POST.get('keywords', post.keywords)
        post.tone = request.POST.get('tone', post.tone)
        post.stylist_id = request.POST.get('stylist_id', post.stylist_id)
        post.coupon_name = request.POST.get('coupon_name', post.coupon_name)
        post.save()
        
        messages.success(request, '記事を更新しました')
        return redirect('blog:post_detail', pk=post.pk)
    
    context = {
        'post': post,
        'tone_choices': [
            ('friendly', 'フレンドリー'),
            ('professional', 'プロフェッショナル'),
            ('casual', 'カジュアル'),
            ('formal', 'フォーマル'),
        ],
    }
    
    return render(request, 'blog/edit.html', context)


@login_required
def post_delete(request, pk):
    """
    Blog post delete view.
    """
    post = get_object_or_404(BlogPost, pk=pk, user=request.user)
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, '記事を削除しました')
        return redirect('blog:post_list')
    
    return render(request, 'blog/delete_confirm.html', {'post': post})


@login_required
def post_history(request):
    """
    Post history/logs view.
    """
    logs = PostLog.objects.filter(user=request.user).order_by('-started_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        logs = logs.filter(status=status_filter)
    
    context = {
        'logs': logs,
        'status_filter': status_filter,
    }
    
    return render(request, 'blog/history.html', context)
