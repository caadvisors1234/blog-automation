# 07. APIエンドポイント設計書 (API Endpoints Design)

## 1. 概要
本ドキュメントは、HPBブログ自動化システムのAPIエンドポイント設計を定義します。
Django REST Frameworkを使用したRESTful APIを提供します。

---

## 2. アーキテクチャ

### 2.1 API設計原則
- **RESTful**: リソース指向のURL設計
- **ViewSet**: Django REST FrameworkのViewSetを活用
- **Router**: DefaultRouterによる自動URL生成
- **認証**: Session認証 + Supabase JWT

### 2.2 URL構造

```
/api/
  /accounts/
    /users/                    # ユーザー情報
    /users/me/                 # 現在のユーザー
    /salon-board-accounts/     # SALON BOARDアカウント
    /salon-board-accounts/current/  # 現在のアカウント

  /blog/
    /posts/                    # ブログ投稿CRUD
    /posts/{id}/generate/      # AI生成トリガー
    /posts/{id}/publish/       # 投稿トリガー
    /posts/{id}/images/        # 画像管理
    /images/                   # 画像CRUD
    /logs/                     # 投稿ログ（読み取り専用）

/admin/                        # Django管理画面
```

---

## 3. アカウント関連API

### 3.1 GET /api/accounts/users/me/

現在のユーザー情報を取得

**レスポンス**:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "first_name": "",
  "last_name": "",
  "supabase_user_id": "uuid-string",
  "hpb_salon_url": "https://beauty.hotpepper.jp/slnH000123456/",
  "hpb_salon_id": "H000123456",
  "date_joined": "2025-01-20T12:00:00Z",
  "has_salon_board_account": true
}
```

---

### 3.2 PATCH /api/accounts/users/me/

ユーザー情報を更新

**リクエスト**:
```json
{
  "username": "newusername",
  "email": "new@example.com",
  "hpb_salon_url": "https://beauty.hotpepper.jp/slnH000999999/"
}
```

**レスポンス**: 更新後のユーザー情報

**注意**: `hpb_salon_id`は`hpb_salon_url`から自動抽出されます

---

### 3.3 GET /api/accounts/salon-board-accounts/current/

現在のSALON BOARDアカウントを取得

**レスポンス**:
```json
{
  "id": 1,
  "login_id": "salon_login_id",
  "is_active": true,
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z"
}
```

---

### 3.4 POST /api/accounts/salon-board-accounts/

SALON BOARDアカウントを作成

**リクエスト**:
```json
{
  "login_id": "salon_login_id",
  "password": "plain_text_password",
  "is_active": true
}
```

**レスポンス**:
```json
{
  "id": 1,
  "login_id": "salon_login_id",
  "is_active": true,
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z"
}
```

**注意**: パスワードは暗号化して保存されます

---

### 3.5 PATCH /api/accounts/salon-board-accounts/{id}/

SALON BOARDアカウントを更新

**リクエスト**:
```json
{
  "login_id": "new_login_id",
  "password": "new_password",
  "is_active": true
}
```

---

### 3.6 DELETE /api/accounts/salon-board-accounts/{id}/

SALON BOARDアカウントを削除

---

## 4. ブログ投稿API

### 4.1 GET /api/blog/posts/

ブログ投稿一覧を取得

**クエリパラメータ**:
| パラメータ | 型 | 説明 |
|-----------|-----|------|
| status | string | ステータスでフィルタ（draft, generating, ready, publishing, published, failed） |
| ai_generated | boolean | AI生成フラグでフィルタ |
| search | string | タイトル・本文で検索 |
| page | integer | ページ番号 |

**レスポンス**:
```json
{
  "count": 100,
  "next": "http://localhost:8000/api/blog/posts/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "ブログタイトル",
      "status": "published",
      "ai_generated": true,
      "author_name": "testuser",
      "image_count": 2,
      "stylist_id": "T000123456",
      "coupon_name": "カット＋カラー",
      "published_at": "2025-01-20T15:00:00Z",
      "created_at": "2025-01-20T12:00:00Z",
      "updated_at": "2025-01-20T15:00:00Z"
    }
  ]
}
```

---

### 4.2 POST /api/blog/posts/

ブログ投稿を作成

**リクエスト（multipart/form-data）**:
```
title: ブログタイトル（25文字以内）
content: 本文
ai_prompt: AIプロンプト
tone: friendly
keywords: カット カラー
stylist_id: T000123456
coupon_name: カット＋カラー
images[]: (File) image1.jpg
images[]: (File) image2.jpg
```

**または JSON**:
```json
{
  "title": "ブログタイトル",
  "content": "本文",
  "ai_prompt": "AIプロンプト",
  "tone": "friendly",
  "keywords": "カット カラー",
  "stylist_id": "T000123456",
  "coupon_name": "カット＋カラー"
}
```

**レスポンス**:
```json
{
  "id": 1,
  "title": "ブログタイトル",
  "content": "本文",
  "status": "draft",
  "ai_generated": true,
  "created_at": "2025-01-20T12:00:00Z"
}
```

---

### 4.3 GET /api/blog/posts/{id}/

ブログ投稿詳細を取得

**レスポンス**:
```json
{
  "id": 1,
  "title": "ブログタイトル",
  "content": "本文",
  "generated_content": "AI生成元本文",
  "status": "ready",
  "ai_prompt": "AIプロンプト",
  "tone": "friendly",
  "keywords": "カット カラー",
  "ai_generated": true,
  "stylist_id": "T000123456",
  "coupon_name": "カット＋カラー",
  "celery_task_id": "550e8400-e29b-41d4-a716-446655440000",
  "salon_board_url": "",
  "published_at": null,
  "author_name": "testuser",
  "author_email": "test@example.com",
  "images": [
    {
      "id": 1,
      "image_file": "/media/blog_images/2025/01/20/image1.jpg",
      "image_url": "/media/blog_images/2025/01/20/image1.jpg",
      "order": 0,
      "uploaded_at": "2025-01-20T12:00:00Z"
    }
  ],
  "log": null,
  "created_at": "2025-01-20T12:00:00Z",
  "updated_at": "2025-01-20T12:00:00Z"
}
```

---

### 4.4 PATCH /api/blog/posts/{id}/

ブログ投稿を更新

**リクエスト**:
```json
{
  "title": "新しいタイトル",
  "content": "新しい本文",
  "status": "ready",
  "stylist_id": "T000999999"
}
```

**ステータス遷移ルール**:
| 現在のステータス | 遷移可能なステータス |
|----------------|-------------------|
| draft | generating, ready, failed |
| generating | ready, failed, draft |
| ready | publishing, draft |
| publishing | published, failed |
| published | （変更不可） |
| failed | draft, generating |

---

### 4.5 DELETE /api/blog/posts/{id}/

ブログ投稿を削除

**注意**: 関連する画像も削除されます

---

### 4.6 POST /api/blog/posts/{id}/generate/

AI記事生成を開始

**前提条件**:
- ステータスが`draft`または`failed`
- `ai_prompt`または`keywords`が設定されている

**レスポンス**:
```json
{
  "detail": "AI content generation started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "post_id": 1,
  "status": "generating"
}
```

**エラーレスポンス**:
```json
{
  "detail": "Post must be in draft or failed status to generate"
}
```

---

### 4.7 POST /api/blog/posts/{id}/publish/

SALON BOARDへの投稿を開始

**前提条件**:
- ステータスが`ready`または`failed`
- タイトルと本文が設定されている
- SALON BOARDアカウントが設定されている

**レスポンス**:
```json
{
  "detail": "SALON BOARD publishing started",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "post_id": 1,
  "log_id": 1,
  "status": "publishing"
}
```

---

### 4.8 GET /api/blog/posts/{id}/images/

投稿の画像一覧を取得

**レスポンス**:
```json
[
  {
    "id": 1,
    "image_file": "/media/blog_images/2025/01/20/image1.jpg",
    "image_url": "/media/blog_images/2025/01/20/image1.jpg",
    "order": 0,
    "uploaded_at": "2025-01-20T12:00:00Z"
  }
]
```

---

### 4.9 POST /api/blog/posts/{id}/images/

画像を追加

**リクエスト（multipart/form-data）**:
```
image: (File) image.jpg
```

**レスポンス**:
```json
{
  "id": 2,
  "image_file": "/media/blog_images/2025/01/20/image2.jpg",
  "image_url": "/media/blog_images/2025/01/20/image2.jpg",
  "order": 1,
  "uploaded_at": "2025-01-20T12:00:00Z"
}
```

**エラー（4枚超過時）**:
```json
{
  "detail": "Maximum 4 images allowed per post"
}
```

---

## 5. 画像API

### 5.1 GET /api/blog/images/{id}/

画像詳細を取得

### 5.2 PATCH /api/blog/images/{id}/

画像を更新（順序変更など）

### 5.3 DELETE /api/blog/images/{id}/

画像を削除

---

## 6. ログAPI

### 6.1 GET /api/blog/logs/

投稿ログ一覧を取得

**クエリパラメータ**:
| パラメータ | 型 | 説明 |
|-----------|-----|------|
| status | string | ステータスでフィルタ（success, failed） |
| page | integer | ページ番号 |

**レスポンス**:
```json
{
  "count": 50,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "blog_post": 1,
      "blog_post_title": "ブログタイトル",
      "user": 1,
      "username": "testuser",
      "status": "success",
      "error_message": "",
      "screenshot_path": "/tmp/screenshot_123.png",
      "scraping_data": {},
      "duration_seconds": 45,
      "started_at": "2025-01-20T12:00:00Z",
      "completed_at": "2025-01-20T12:00:45Z"
    }
  ]
}
```

---

### 6.2 GET /api/blog/logs/{id}/

ログ詳細を取得

---

## 7. エラーレスポンス

### 7.1 HTTPステータスコード

| コード | 意味 | 使用場面 |
|--------|------|---------|
| 200 | OK | 成功 |
| 201 | Created | リソース作成成功 |
| 202 | Accepted | 非同期処理受付 |
| 400 | Bad Request | バリデーションエラー |
| 401 | Unauthorized | 未認証 |
| 403 | Forbidden | 権限なし |
| 404 | Not Found | リソース不存在 |
| 500 | Internal Server Error | サーバーエラー |

### 7.2 エラーレスポンス形式

```json
{
  "detail": "エラーメッセージ"
}
```

または（バリデーションエラー）:
```json
{
  "title": ["This field may not be blank."],
  "content": ["This field is required."]
}
```

---

## 8. 認証

### 8.1 認証方式

- **Session認証**: Django標準のセッション認証
- **Supabase JWT**: カスタム認証バックエンドで検証

### 8.2 認証ヘッダー

```
Authorization: Bearer <supabase_jwt_token>
```

### 8.3 CSRF保護

```javascript
// CSRFトークンの取得
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

// APIリクエスト
fetch('/api/blog/posts/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
});
```

---

## 9. URL設定

### 9.1 config/urls.py

```python
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/accounts/', include('apps.accounts.urls')),
    path('api/blog/', include('apps.blog.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
```

### 9.2 apps/accounts/urls.py

```python
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
```

### 9.3 apps/blog/urls.py

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BlogPostViewSet, BlogImageViewSet, PostLogViewSet

app_name = 'blog'

router = DefaultRouter()
router.register(r'posts', BlogPostViewSet, basename='post')
router.register(r'images', BlogImageViewSet, basename='image')
router.register(r'logs', PostLogViewSet, basename='log')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## 10. まとめ

このAPI設計により：
- **RESTful設計**: リソース指向の直感的なURL
- **ViewSet活用**: コードの再利用性と一貫性
- **自動ルーティング**: DRF Routerによる効率的なURL管理
- **セキュリティ**: 認証・認可、CSRF保護
- **非同期処理**: Celeryタスクによる重い処理の分離

---

**作成日**: 2025年1月
**最終更新**: 2025年11月
**ステータス**: 実装完了・ドキュメント更新
