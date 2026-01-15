# -*- coding: utf-8 -*-
import json
import tempfile
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.test.utils import override_settings
from apps.blog.models import BlogPost, BlogImage


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class BlogImageReorderApiTests(TestCase):
    """Test image reorder API."""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create(
            username='image-order-user',
            email='image-order@example.com',
            supabase_user_id='supabase-image-order'
        )
        self.client.force_login(self.user)

        self.post = BlogPost.objects.create(
            user=self.user,
            title='テスト記事',
            content='{{image_1}}本文{{image_2}}',
            status='draft'
        )

    def create_image(self, order: int) -> BlogImage:
        image_file = SimpleUploadedFile(
            f'test_{order}.png',
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc'
            b'\x00\x00\x00\x02\x00\x01\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82',
            content_type='image/png'
        )
        return BlogImage.objects.create(
            blog_post=self.post,
            image_file=image_file,
            order=order
        )

    def test_reorder_images(self):
        image_one = self.create_image(0)
        image_two = self.create_image(1)
        image_three = self.create_image(2)

        payload = {
            'post_id': self.post.id,
            'orders': [
                {'id': image_three.id, 'order': 0},
                {'id': image_one.id, 'order': 1},
                {'id': image_two.id, 'order': 2},
            ]
        }

        response = self.client.post(
            '/api/blog/images/reorder/',
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        reordered = list(
            BlogImage.objects.filter(blog_post=self.post).order_by('order').values_list('id', flat=True)
        )
        self.assertEqual(reordered, [image_three.id, image_one.id, image_two.id])
