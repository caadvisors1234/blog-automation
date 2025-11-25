"""
Tests for Blog app API endpoints - Stats
"""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.blog.models import BlogPost


class BlogPostStatsAPITestCase(TestCase):
    """Tests for the BlogPost stats API endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        
        # Create another user for isolation test
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpassword123'
        )
        
        # Create some blog posts for test user
        self.posts = []
        statuses = ['draft', 'draft', 'generating', 'ready', 'published', 'published', 'failed']
        for i, post_status in enumerate(statuses):
            post = BlogPost.objects.create(
                user=self.user,
                title=f'Test Post {i+1}',
                content=f'Content for test post {i+1}',
                status=post_status,
            )
            self.posts.append(post)
        
        # Create posts for other user (should not appear in stats)
        BlogPost.objects.create(
            user=self.other_user,
            title='Other User Post',
            content='This should not be counted',
            status='published',
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_stats_endpoint_requires_authentication(self):
        """Test that stats endpoint requires authentication"""
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_stats_endpoint_returns_correct_totals(self):
        """Test that stats endpoint returns correct total counts"""
        self.client.force_authenticate(user=self.user)
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Total posts for this user should be 7
        self.assertEqual(data['total'], 7)
    
    def test_stats_endpoint_calculates_success_rate(self):
        """Test that stats endpoint calculates correct success rate"""
        self.client.force_authenticate(user=self.user)
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Success rate should be 2/(2+1) = 66.67% ≈ 67%
        # published=2, failed=1
        expected_rate = round((2 / (2 + 1)) * 100)  # 67
        self.assertEqual(data['success_rate'], expected_rate)
    
    def test_stats_endpoint_returns_this_month_count(self):
        """Test that stats endpoint returns correct this_month count"""
        self.client.force_authenticate(user=self.user)
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All 7 posts were created this month (in setUp)
        self.assertEqual(data['this_month'], 7)
    
    def test_stats_endpoint_isolates_user_data(self):
        """Test that stats only includes current user's posts"""
        self.client.force_authenticate(user=self.other_user)
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Other user should only see their own 1 post
        self.assertEqual(data['total'], 1)
    
    def test_stats_with_no_posts(self):
        """Test stats endpoint with user who has no posts"""
        # Create a new user with no posts
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpassword123'
        )
        
        self.client.force_authenticate(user=new_user)
        url = reverse('blog_api:post-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['this_month'], 0)
        self.assertEqual(data['success_rate'], 0)


class BlogPostListTestCase(TestCase):
    """Tests for BlogPost list/create endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.client = APIClient()
    
    def test_list_posts_requires_authentication(self):
        """Test that list endpoint requires authentication"""
        url = reverse('blog_api:post-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_list_posts_returns_user_posts(self):
        """Test that list endpoint returns only user's posts"""
        # Create posts
        BlogPost.objects.create(
            user=self.user,
            title='User Post',
            content='Content',
            status='draft'
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('blog_api:post-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should return paginated results
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], 'User Post')
    
    def test_create_post(self):
        """Test creating a new blog post via API"""
        self.client.force_authenticate(user=self.user)
        url = reverse('blog_api:post-list')
        
        data = {
            'title': 'New Blog Post',
            'content': 'This is the content',
            'keywords': 'test, blog, api',
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify the post was created with correct user
        post = BlogPost.objects.get(title='New Blog Post')
        self.assertEqual(post.user, self.user)
        self.assertEqual(post.status, 'draft')

