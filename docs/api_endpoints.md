# 07. APIエンドポイント設計書 (API Endpoints Design)

## 1. 概要
本ドキュメントは、HPBブログ自動化システムのAPIエンドポイントとURL設計を定義します。
基本はDjangoテンプレートによるサーバーサイドレンダリングですが、AJAX通信用のREST APIエンドポイントも提供します。

---

## 2. URL構成方針

### 2.1 URL設計原則
- **RESTful**: リソース指向のURL設計
- **直感的**: URLから機能が推測できる
- **階層的**: 親子関係を明確に
- **一貫性**: 命名規則を統一

### 2.2 URL構造

```
/                           # トップページ（ダッシュボード）
/accounts/                  # 認証関連
  /login/                   # ログイン
  /signup/                  # サインアップ
  /logout/                  # ログアウト
  /settings/                # ユーザー設定

/blog/                      # ブログ投稿関連
  /                         # 投稿一覧
  /create/                  # 新規作成
  /{id}/                    # 投稿詳細
  /{id}/edit/               # 編集
  /{id}/delete/             # 削除
  /history/                 # 投稿履歴

/api/                       # REST API（AJAX用）
  /blog/
    /create/                # ブログ作成API
    /{id}/status/           # ステータス取得
  /tasks/
    /{task_id}/status/      # タスクステータス取得

/ws/                        # WebSocket
  /blog/progress/           # 進捗通知

/health/                    # ヘルスチェック
```

---

## 3. エンドポイント詳細

### 3.1 認証関連エンドポイント

#### POST /accounts/login/

ユーザーログイン

**リクエスト（Form Data）**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**レスポンス（成功）**:
```http
HTTP/1.1 302 Found
Location: /
```

**レスポンス（失敗）**:
```html
<!-- login.htmlにエラーメッセージ表示 -->
```

**実装例**:
```python
# apps/accounts/views.py
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Supabase認証
        try:
            supabase = get_supabase_client()
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.session:
                # Django認証
                from apps.accounts.backends import SupabaseAuthBackend
                backend = SupabaseAuthBackend()
                user = backend.authenticate(
                    request,
                    token=response.session.access_token
                )

                if user:
                    login(request, user)
                    return redirect('dashboard')

        except Exception as e:
            messages.error(request, 'ログインに失敗しました')

    return render(request, 'accounts/login.html')
```

---

#### POST /accounts/signup/

新規ユーザー登録

**リクエスト（Form Data）**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "password_confirm": "password123"
}
```

**レスポンス（成功）**:
```http
HTTP/1.1 302 Found
Location: /accounts/login/
```

---

#### POST /accounts/logout/

ログアウト

**レスポンス**:
```http
HTTP/1.1 302 Found
Location: /accounts/login/
```

---

#### GET/POST /accounts/settings/

ユーザー設定管理

**ページ表示（GET）**:
現在の設定を表示

**設定更新（POST）**:
```json
{
  "hpb_salon_url": "https://beauty.hotpepper.jp/slnH000xxxxx/",
  "salonboard_user_id": "login_id",
  "salonboard_password": "password"
}
```

**レスポンス**:
```http
HTTP/1.1 302 Found
Location: /accounts/settings/
```

**実装例**:
```python
# apps/accounts/views.py
from django.contrib.auth.decorators import login_required
import re

@login_required
def settings_view(request):
    if request.method == 'POST':
        user = request.user

        # HPBサロンURL
        hpb_url = request.POST.get('hpb_salon_url', '').strip()
        if hpb_url:
            # サロンIDを抽出
            match = re.search(r'slnH?(\d+)', hpb_url)
            if match:
                user.hpb_salon_id = 'H' + match.group(1)
            user.hpb_salon_url = hpb_url

        # SALON BOARD認証情報
        sb_user_id = request.POST.get('salonboard_user_id', '').strip()
        sb_password = request.POST.get('salonboard_password', '').strip()

        if sb_user_id and sb_password:
            user.save_credentials(sb_user_id, sb_password)
        else:
            user.save()

        messages.success(request, '設定を更新しました')
        return redirect('accounts:settings')

    return render(request, 'accounts/settings.html')
```

---

### 3.2 ブログ投稿関連エンドポイント

#### GET /blog/

投稿一覧ページ

**レスポンス**: HTML（テンプレート: `blog/list.html`）

**実装例**:
```python
# apps/blog/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.blog.models import BlogPost

@login_required
def blog_list_view(request):
    posts = BlogPost.objects.filter(
        user=request.user
    ).select_related('user').prefetch_related('images').order_by('-created_at')

    context = {
        'posts': posts
    }
    return render(request, 'blog/list.html', context)
```

---

#### GET /blog/create/

新規投稿作成ページ

**レスポンス**: HTML（テンプレート: `blog/create.html`）

**実装例**:
```python
@login_required
def blog_create_view(request):
    # スタイリスト・クーポン情報をフォーム用に準備
    user = request.user

    context = {
        'tone_choices': [
            ('friendly', '親しみやすい'),
            ('professional', 'プロフェッショナル'),
            ('casual', 'カジュアル'),
        ]
    }
    return render(request, 'blog/create.html', context)
```

---

#### GET /blog/{id}/

投稿詳細ページ

**レスポンス**: HTML（テンプレート: `blog/detail.html`）

**実装例**:
```python
from django.shortcuts import get_object_or_404

@login_required
def blog_detail_view(request, pk):
    post = get_object_or_404(
        BlogPost.objects.select_related('user', 'log').prefetch_related('images'),
        pk=pk,
        user=request.user
    )

    context = {
        'post': post
    }
    return render(request, 'blog/detail.html', context)
```

---

#### GET /blog/history/

投稿履歴ページ

**レスポンス**: HTML（テンプレート: `blog/history.html`）

**実装例**:
```python
@login_required
def blog_history_view(request):
    logs = PostLog.objects.filter(
        user=request.user
    ).select_related('blog_post').order_by('-started_at')

    context = {
        'logs': logs
    }
    return render(request, 'blog/history.html', context)
```

---

### 3.3 REST APIエンドポイント（AJAX用）

#### POST /api/blog/create/

ブログ作成API（非同期）

**リクエスト（multipart/form-data）**:
```
keywords: "カット カラー トリートメント"
tone: "friendly"
stylist_id: "T000123456"
coupon_name: "カット＋カラー"
images[]: (File) image1.jpg
images[]: (File) image2.jpg
```

**レスポンス（成功）**:
```json
{
  "status": "success",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "blog_post_id": 123,
  "title": "生成されたタイトル",
  "message": "ブログ作成タスクを開始しました"
}
```

**レスポンス（エラー）**:
```json
{
  "status": "error",
  "error": "画像は最大4枚までです",
  "code": "VALIDATION_ERROR"
}
```

**実装例**:
```python
# apps/blog/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from apps.blog.models import BlogPost, BlogImage
from apps.blog.tasks import auto_post_blog_task
from apps.blog.ai_generator import generate_blog_content
import json

@login_required
@csrf_exempt  # CSRFトークンはヘッダーで送信
def api_blog_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # パラメータ取得
        keywords = request.POST.get('keywords', '').strip()
        tone = request.POST.get('tone', 'friendly')
        stylist_id = request.POST.get('stylist_id', '').strip()
        coupon_name = request.POST.get('coupon_name', '').strip()
        images = request.FILES.getlist('images')

        # バリデーション
        if not keywords:
            return JsonResponse({
                'status': 'error',
                'error': 'キーワードは必須です',
                'code': 'VALIDATION_ERROR'
            }, status=400)

        if len(images) == 0:
            return JsonResponse({
                'status': 'error',
                'error': '画像を少なくとも1枚アップロードしてください',
                'code': 'VALIDATION_ERROR'
            }, status=400)

        if len(images) > 4:
            return JsonResponse({
                'status': 'error',
                'error': '画像は最大4枚までです',
                'code': 'VALIDATION_ERROR'
            }, status=400)

        # AI記事生成
        content = generate_blog_content(
            keywords=keywords,
            tone=tone,
            image_count=len(images)
        )

        # BlogPost作成
        blog_post = BlogPost.objects.create(
            user=request.user,
            title=content['title'],
            body=content['body'],
            generated_body=content['body'],
            tone=tone,
            keywords=keywords,
            stylist_id=stylist_id,
            coupon_name=coupon_name,
            status='processing'
        )

        # 画像保存
        image_paths = []
        for idx, image_file in enumerate(images):
            blog_image = BlogImage.objects.create(
                blog_post=blog_post,
                image_file=image_file,
                order=idx
            )
            image_paths.append(blog_image.file_path)

        # Celeryタスク起動
        task = auto_post_blog_task.delay(
            user_id=request.user.id,
            title=blog_post.title,
            body=blog_post.body,
            image_paths=image_paths,
            stylist_id=stylist_id,
            coupon_name=coupon_name
        )

        # タスクIDを保存
        blog_post.celery_task_id = task.id
        blog_post.save(update_fields=['celery_task_id'])

        return JsonResponse({
            'status': 'success',
            'task_id': task.id,
            'blog_post_id': blog_post.id,
            'title': blog_post.title,
            'message': 'ブログ作成タスクを開始しました'
        })

    except Exception as e:
        logger.error(f"API error: {e}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'code': 'INTERNAL_ERROR'
        }, status=500)
```

---

#### GET /api/blog/{id}/status/

ブログ投稿ステータス取得

**レスポンス**:
```json
{
  "status": "completed",
  "blog_post_id": 123,
  "title": "タイトル",
  "posted_at": "2025-01-20T12:34:56Z",
  "screenshot_url": "/media/screenshots/1234567890.png"
}
```

**実装例**:
```python
@login_required
def api_blog_status(request, pk):
    try:
        post = BlogPost.objects.select_related('log').get(
            pk=pk,
            user=request.user
        )

        response_data = {
            'status': post.status,
            'blog_post_id': post.id,
            'title': post.title,
            'posted_at': post.posted_at.isoformat() if post.posted_at else None
        }

        if post.log:
            response_data['screenshot_url'] = post.log.screenshot_path
            response_data['error_message'] = post.log.error_message

        return JsonResponse(response_data)

    except BlogPost.DoesNotExist:
        return JsonResponse({
            'error': 'Blog post not found'
        }, status=404)
```

---

#### GET /api/tasks/{task_id}/status/

Celeryタスクステータス取得

**レスポンス**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "screenshot_path": "/media/screenshots/1234567890.png"
  }
}
```

**実装例**:
```python
from celery.result import AsyncResult

@login_required
def api_task_status(request, task_id):
    task = AsyncResult(task_id)

    response_data = {
        'task_id': task_id,
        'status': task.status,
        'result': None
    }

    if task.status == 'SUCCESS':
        response_data['result'] = task.result
    elif task.status == 'FAILURE':
        response_data['error'] = str(task.info)

    return JsonResponse(response_data)
```

---

### 3.4 WebSocketエンドポイント

#### WS /ws/blog/progress/

リアルタイム進捗通知

**接続**:
```javascript
const socket = new WebSocket('ws://localhost:8000/ws/blog/progress/');
```

**受信メッセージ（進捗）**:
```json
{
  "type": "task_progress",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "posting",
  "progress": 60,
  "message": "ログイン中...",
  "data": {}
}
```

**受信メッセージ（エラー）**:
```json
{
  "type": "task_error",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "error": "Login failed",
  "message": "投稿中にエラーが発生しました"
}
```

---

### 3.5 ヘルスチェックエンドポイント

#### GET /health/

システムヘルスチェック

**レスポンス**:
```json
{
  "status": "healthy",
  "database": "ok",
  "redis": "ok",
  "celery": "ok",
  "timestamp": "2025-01-20T12:34:56Z"
}
```

**実装例**:
```python
# apps/core/views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from celery import current_app
from datetime import datetime

def health_check(request):
    health = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }

    # Database check
    try:
        connection.ensure_connection()
        health['database'] = 'ok'
    except Exception as e:
        health['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'

    # Redis check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['redis'] = 'ok'
        else:
            health['redis'] = 'error'
            health['status'] = 'unhealthy'
    except Exception as e:
        health['redis'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'

    # Celery check
    try:
        inspector = current_app.control.inspect()
        stats = inspector.stats()
        if stats:
            health['celery'] = 'ok'
        else:
            health['celery'] = 'no workers'
            health['status'] = 'degraded'
    except Exception as e:
        health['celery'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'

    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)
```

---

## 4. URL設定ファイル

### 4.1 config/urls.py（ルート）

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.core.views import health_check, dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('accounts/', include('apps.accounts.urls')),
    path('blog/', include('apps.blog.urls')),
    path('api/', include('apps.blog.api_urls')),
    path('health/', health_check, name='health'),
]

# メディアファイル配信（開発環境のみ）
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### 4.2 apps/accounts/urls.py

```python
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('settings/', views.settings_view, name='settings'),
]
```

### 4.3 apps/blog/urls.py

```python
from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.blog_list_view, name='list'),
    path('create/', views.blog_create_view, name='create'),
    path('<int:pk>/', views.blog_detail_view, name='detail'),
    path('<int:pk>/edit/', views.blog_edit_view, name='edit'),
    path('<int:pk>/delete/', views.blog_delete_view, name='delete'),
    path('history/', views.blog_history_view, name='history'),
]
```

### 4.4 apps/blog/api_urls.py

```python
from django.urls import path
from . import views

app_name = 'blog_api'

urlpatterns = [
    path('blog/create/', views.api_blog_create, name='create'),
    path('blog/<int:pk>/status/', views.api_blog_status, name='status'),
    path('tasks/<str:task_id>/status/', views.api_task_status, name='task_status'),
]
```

---

## 5. エラーレスポンス

### 5.1 HTTPステータスコード

| コード | 意味 | 使用場面 |
|--------|------|---------|
| 200 | OK | 成功 |
| 201 | Created | リソース作成成功 |
| 302 | Found | リダイレクト |
| 400 | Bad Request | バリデーションエラー |
| 401 | Unauthorized | 未認証 |
| 403 | Forbidden | 権限なし |
| 404 | Not Found | リソース不存在 |
| 500 | Internal Server Error | サーバーエラー |
| 503 | Service Unavailable | サービス停止中 |

### 5.2 エラーレスポンス形式

```json
{
  "status": "error",
  "error": "エラーメッセージ",
  "code": "ERROR_CODE",
  "details": {
    "field": "field_name",
    "message": "詳細メッセージ"
  }
}
```

**エラーコード一覧**:
- `VALIDATION_ERROR`: バリデーションエラー
- `AUTHENTICATION_ERROR`: 認証エラー
- `PERMISSION_ERROR`: 権限エラー
- `NOT_FOUND`: リソース不存在
- `INTERNAL_ERROR`: サーバー内部エラー

---

## 6. 認証・認可

### 6.1 認証方式

#### テンプレートページ
- **セッション認証**: Django標準のセッション
- **デコレータ**: `@login_required`

#### REST API
- **セッション認証**: CSRF保護付き
- **ヘッダー**: `X-CSRFToken: <token>`

#### WebSocket
- **セッション認証**: Cookie経由
- **認証チェック**: コンシューマーの`connect()`

### 6.2 CSRF保護

```python
# settings.py
CSRF_COOKIE_HTTPONLY = False  # JavaScriptからアクセス可能
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = ['https://your-domain.com']
```

```javascript
// フロントエンド
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

fetch('/api/blog/create/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken
    },
    body: formData
});
```

---

## 7. レート制限

### 7.1 django-ratelimitの使用

```bash
pip install django-ratelimit
```

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='10/m', method='POST')
@login_required
def api_blog_create(request):
    # ...
    pass
```

### 7.2 制限値

| エンドポイント | レート | 備考 |
|--------------|--------|------|
| POST /api/blog/create/ | 10回/分 | ユーザー単位 |
| GET /api/tasks/{id}/status/ | 30回/分 | ユーザー単位 |
| POST /accounts/login/ | 5回/分 | IP単位 |

---

## 8. まとめ

このAPI設計により：
- **明確なURL構造**: RESTful原則に従った直感的なURL
- **セキュリティ**: CSRF保護、認証・認可、レート制限
- **リアルタイム性**: WebSocketによる進捗通知
- **監視性**: ヘルスチェックエンドポイント
- **拡張性**: APIとテンプレートの共存

次のステップでは、フロントエンド画面設計を行います。

---

**作成日**: 2025年1月
**最終更新**: 2025年1月
**ステータス**: 初版完成
