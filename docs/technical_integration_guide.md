# 04. 技術統合設計書 (Technical Integration Guide)

## 1. 概要
本ドキュメントは、HPBブログ自動化システムにおける各技術要素の統合方法を詳細に定義します。
Google Gemini 2.5 Flash、Supabase Auth、Django、Celery、Redis、Playwrightを組み合わせた実装ガイドです。

### 1.1 設計方針（ヒアリング結果反映）

#### フロントエンド
- **レンダリング方式**: サーバーサイドレンダリング（Django Template + Tailwind CSS）
- **リアルタイム通信**: Django Channels（WebSocket）を使用
- **進捗表示**: WebSocket経由でリアルタイム更新

#### ストレージ
- **画像保存**: ローカルファイルシステム（`/media`ディレクトリ）
- **画像処理**: リサイズ・最適化なし（アップロードされたまま使用）

#### データ取得戦略
- **マスタデータ**: 毎回投稿時にスクレイピング（キャッシュなし）
- **スタイリスト情報**: 投稿直前に取得
- **クーポン情報**: 投稿直前に取得

#### 通知方式
- **エラー通知**: ダッシュボード内の通知のみ（メール・Slack不要）
- **進捗通知**: WebSocketでリアルタイム表示

#### デプロイ環境
- **VPSプロバイダー**: ConoHa VPS
- **利用形態**: 複数ユーザー同時利用想定
- **推奨スペック**:
  - CPU: 4コア以上
  - メモリ: 8GB以上
  - ストレージ: SSD 100GB以上

---

## 2. Google Gemini 2.5 Flash 統合

### 2.1 公式SDK情報
- **ライブラリ**: `google-genai` (Google Gen AI Python SDK)
- **ドキュメント**: https://github.com/googleapis/python-genai
- **インストール**: `pip install google-genai`

### 2.2 初期化とセットアップ

```python
from google import genai
from google.genai import types
import os

# 環境変数から APIキーを取得（推奨）
os.environ['GEMINI_API_KEY'] = 'your-api-key'
client = genai.Client()

# または明示的にAPIキーを指定
client = genai.Client(api_key='your-api-key')
```

### 2.3 ブログ記事生成の実装（3案生成対応）

現在の実装では、AIが3つの異なる記事バリエーションを生成し、ユーザーが選択できるようになっています。

#### 3案生成メソッド
```python
# apps/blog/gemini_client.py
from google import genai
from google.genai import types
import json
import re

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_id = 'gemini-2.5-flash'

    def generate_blog_content_variations(
        self,
        prompt: str,
        num_variations: int = 3,
        image_count: int = 0,
        temperature: float = 0.9,
        max_output_tokens: int = 8192,
    ) -> dict:
        """
        3種類の異なる記事バリエーションを生成

        Args:
            prompt: ユーザーからのリクエスト
            num_variations: 生成するバリエーション数（デフォルト3）
            image_count: 画像の枚数（プレースホルダー挿入用）
            temperature: 創造性レベル（0.0-1.0）
            max_output_tokens: 最大出力トークン数

        Returns:
            dict: {"variations": [{"id": 1, "title": "...", "content": "..."}, ...]}
        """
        # 画像プレースホルダー指示を構築
        image_instruction = ""
        if image_count > 0:
            placeholder_list = ', '.join([f'{{{{image_{i}}}}}' for i in range(1, image_count + 1)])
            image_instruction = f"""

【画像プレースホルダー - 必須】
この記事には{image_count}枚の画像が添付されています。
本文中に以下の{image_count}個のプレースホルダーを【必ず全て】配置してください：
{placeholder_list}

配置ルール：
- 全てのプレースホルダーを必ず使用すること（省略厳禁）
- 記事の流れに合った適切な位置に配置する
- プレースホルダーは単独の行に配置する"""

        system_instruction = f"""あなたは美容サロンのブログライターです。
{num_variations}種類の異なる魅力的なブログ記事を作成してください。

各記事の要件：
- タイトルは25文字以内
- 本文は600-800文字程度
- 3つの記事はそれぞれ異なる切り口で書く{image_instruction}

出力形式：必ずJSON形式で返してください
{{
  "variations": [
    {{"title": "...", "content": "..."}},
    ...
  ]
}}"""

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                response_mime_type="application/json",
                system_instruction=system_instruction,
            )
        )

        # JSONパースとバリデーション
        result = self._extract_json_from_text(response.text)
        variations = []
        
        for i, var in enumerate(result.get('variations', [])[:num_variations]):
            content = self._clean_content(var.get('content', ''))
            
            # 画像プレースホルダーの保証
            if image_count > 0:
                content = self._ensure_image_placeholders(content, image_count)
            
            variations.append({
                'id': i + 1,
                'title': var.get('title', '')[:25],
                'content': content,
            })

        return {'variations': variations, 'success': True}
```

#### 画像プレースホルダー保証機能
```python
def _ensure_image_placeholders(self, content: str, image_count: int) -> str:
    """
    画像プレースホルダーが確実に含まれることを保証

    AIが一部のプレースホルダーを省略した場合でも、
    この後処理で不足分を補完する。
    """
    if image_count <= 0:
        return content

    # 既存のプレースホルダーを検出
    existing = set()
    for i in range(1, image_count + 1):
        patterns = [f'{{{{image_{i}}}}}', f'{{image_{i}}}', f'[[image_{i}]]']
        if any(p in content for p in patterns):
            existing.add(i)

    # 不足分を検出
    missing = [i for i in range(1, image_count + 1) if i not in existing]

    if not missing:
        return content

    # 段落間に均等配置
    paragraphs = content.split('\n\n')
    for idx, img_num in enumerate(missing):
        insert_pos = min(
            (idx + 1) * len(paragraphs) // (len(missing) + 1),
            len(paragraphs) - 1
        )
        paragraphs[insert_pos] += f'\n\n{{{{image_{img_num}}}}}'

    return '\n\n'.join(paragraphs)
```

#### JSON抽出ヘルパー（堅牢なパース）
```python
def _extract_json_from_text(self, text: str) -> dict:
    """
    様々な形式のAI出力からJSONを抽出

    対応形式:
    - 純粋なJSON
    - Markdownコードブロック内のJSON
    - 前後に説明文があるJSON
    """
    if not text:
        return {}

    # 直接パースを試行
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Markdownコードブロックから抽出
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

    return {}
```

#### エラーハンドリング
```python
from google.api_core import exceptions as google_exceptions

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
except google_exceptions.ResourceExhausted:
    # レート制限エラー
    logger.error("Gemini API rate limit exceeded")
    raise
except google_exceptions.InvalidArgument:
    # 不正な引数エラー
    logger.error("Invalid prompt or configuration")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 2.4 コスト管理とベストプラクティス

- **モデル選択**: `gemini-2.5-flash` は高速かつ低コスト
- **トークン数管理**: `max_output_tokens=2000` で制限
- **レート制限**: 無料枠は 60 RPM (Requests Per Minute)
- **キャッシング**: 同じプロンプトの再利用は避ける

---

## 3. Supabase Auth 統合

### 3.1 Django統合アーキテクチャ

**重要な設計決定**:
- Supabaseは**認証のみ**に使用
- ユーザーデータ（UID, 設定等）はPostgreSQLに保存
- JWTトークンでセッション管理
- django-supabase-authパッケージは実験的で非推奨のため、**手動統合を推奨**

### 3.2 Supabaseクライアント設定

```python
# config/supabase.py
from supabase import create_client, Client
from django.conf import settings

def get_supabase_client() -> Client:
    """Supabaseクライアントのシングルトンインスタンスを取得"""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY
    )
```

### 3.3 Django設定

```python
# config/settings.py
import os

# Supabase設定
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')  # 管理用

# 認証バックエンド
AUTHENTICATION_BACKENDS = [
    'apps.accounts.backends.SupabaseAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

### 3.4 カスタム認証バックエンド

```python
# apps/accounts/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from supabase import create_client
from django.conf import settings
import jwt

User = get_user_model()

class SupabaseAuthBackend(BaseBackend):
    """
    SupabaseのJWTトークンを検証してDjangoユーザーを認証
    """

    def authenticate(self, request, token=None, **kwargs):
        if not token:
            return None

        try:
            # JWTトークンを検証
            decoded = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated'
            )

            uid = decoded.get('sub')
            email = decoded.get('email')

            if not uid:
                return None

            # Djangoユーザーの取得または作成
            user, created = User.objects.get_or_create(
                supabase_uid=uid,
                defaults={'email': email, 'username': email}
            )

            return user

        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
```

### 3.5 ユーザーモデル

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import re

class User(AbstractUser):
    """
    Custom user model for Supabase integration and HPB settings
    """
    # Supabase integration
    supabase_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text='User ID from Supabase authentication system'
    )

    # HPB settings
    hpb_salon_url = models.URLField(
        max_length=500,
        blank=True,
        help_text='HPB salon top page URL'
    )
    hpb_salon_id = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text='Extracted salon ID (auto-generated from URL)'
    )

    class Meta:
        db_table = 'accounts_user'
        indexes = [
            models.Index(fields=['supabase_user_id']),
            models.Index(fields=['hpb_salon_id']),
        ]

    def save(self, *args, **kwargs):
        """Auto-extract salon ID from HPB URL"""
        if self.hpb_salon_url and not self.hpb_salon_id:
            match = re.search(r'sln(H\d+)', self.hpb_salon_url)
            if match:
                self.hpb_salon_id = match.group(1)
        super().save(*args, **kwargs)
```

**注意**: SALON BOARD認証情報は別モデル`SALONBoardAccount`で管理します（`apps/blog/models.py`）。

### 3.6 サインアップ・ログインビュー

```python
# apps/accounts/views.py
from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from config.supabase import get_supabase_client
import json

@csrf_exempt
def signup_view(request):
    """
    Supabase経由でユーザーを登録
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return JsonResponse({'error': 'Email and password required'}, status=400)

    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        if response.user:
            return JsonResponse({
                'message': 'User created successfully',
                'uid': response.user.id
            })
        else:
            return JsonResponse({'error': 'Signup failed'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def login_view(request):
    """
    Supabase経由でログイン
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return JsonResponse({'error': 'Email and password required'}, status=400)

    try:
        supabase = get_supabase_client()
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.session:
            # Djangoセッションにトークンを保存
            request.session['access_token'] = response.session.access_token
            request.session['refresh_token'] = response.session.refresh_token

            # Django認証
            from apps.accounts.backends import SupabaseAuthBackend
            backend = SupabaseAuthBackend()
            user = backend.authenticate(
                request,
                token=response.session.access_token
            )

            if user:
                login(request, user)
                return JsonResponse({
                    'message': 'Login successful',
                    'user_id': user.id
                })

        return JsonResponse({'error': 'Login failed'}, status=401)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### 3.7 ミドルウェアでJWT検証

```python
# apps/accounts/middleware.py
from django.utils.deprecation import MiddlewareMixin
from apps.accounts.backends import SupabaseAuthBackend

class SupabaseAuthMiddleware(MiddlewareMixin):
    """
    全てのリクエストでSupabaseトークンを検証
    """

    def process_request(self, request):
        if request.user.is_authenticated:
            return

        token = request.session.get('access_token')
        if token:
            backend = SupabaseAuthBackend()
            user = backend.authenticate(request, token=token)
            if user:
                request.user = user
```

### 3.8 認証情報の暗号化

```python
# apps/accounts/utils.py
from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet():
    """Fernetインスタンスを取得"""
    return Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt_credential(plain_text: str) -> str:
    """認証情報を暗号化"""
    if not plain_text:
        return ""
    f = get_fernet()
    return f.encrypt(plain_text.encode()).decode()

def decrypt_credential(encrypted_text: str) -> str:
    """認証情報を復号化"""
    if not encrypted_text:
        return ""
    f = get_fernet()
    return f.decrypt(encrypted_text.encode()).decode()
```

使用例:
```python
from apps.accounts.utils import encrypt_credential, decrypt_credential

# 保存時
user.salonboard_password = encrypt_credential(plain_password)
user.save()

# 取得時
plain_password = decrypt_credential(user.salonboard_password)
```

---

## 4. Celery + Redis 統合

### 4.1 アーキテクチャ

```
Django Web App → Redis (Broker) → Celery Worker → Playwright
                     ↓
                 Results Backend
```

### 4.2 インストール

```bash
pip install celery redis django-celery-results django-celery-beat
```

### 4.3 Django設定

```python
# config/settings.py
import os

# Redis設定
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Celery設定
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = 'django-db'  # 結果をDjangoのDBに保存
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tokyo'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30分でタイムアウト

# Celery Beat (スケジューリング)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
```

### 4.4 Celery初期化

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('blog_automation')
app.config_from_object('django.conf:settings', namespace='CELERY')

# 全てのDjangoアプリからタスクを自動検出
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```

```python
# config/__init__.py
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 4.5 Playwrightとの統合（重要）

**既知の問題**: CeleryからPlaywrightをインポートする際、順序の問題が発生する可能性があります。

**推奨パターン**:

```python
# apps/blog/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def auto_post_blog_task(
    self,
    user_id: int,
    title: str,
    body: str,
    image_paths: list,
    stylist_id: str,
    coupon_name: str
):
    """
    ブログ自動投稿タスク

    NOTE: Playwrightのインポートはタスク内で行う
    """
    try:
        # Playwrightのインポートはここで行う
        from playwright.sync_api import sync_playwright
        from apps.blog.automation import SalonBoardAutomation
        from apps.accounts.models import User

        logger.info(f"Starting blog post task for user {user_id}")

        # ユーザー情報取得
        user = User.objects.get(id=user_id)

        # 認証情報の復号化
        from apps.accounts.utils import decrypt_credential
        login_id = decrypt_credential(user.salonboard_user_id)
        password = decrypt_credential(user.salonboard_password)

        # 自動投稿実行
        with sync_playwright() as p:
            automation = SalonBoardAutomation(p, login_id, password)
            result = automation.post_blog(
                salon_id=user.hpb_salon_id,
                title=title,
                body=body,
                image_paths=image_paths,
                stylist_id=stylist_id,
                coupon_name=coupon_name
            )

        logger.info(f"Blog post completed for user {user_id}")
        return {
            'status': 'success',
            'screenshot_path': result.get('screenshot_path')
        }

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        # リトライロジック
        raise self.retry(exc=exc, countdown=60)
```

### 4.6 Django Viewからのタスク呼び出し

```python
# apps/blog/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.blog.tasks import auto_post_blog_task
import json

@login_required
def create_and_post_blog(request):
    """
    ブログ作成と自動投稿を開始
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    data = json.loads(request.body)

    # 画像やキーワードから記事生成（同期処理）
    from apps.blog.ai_generator import generate_blog_content
    content = generate_blog_content(
        keywords=data.get('keywords'),
        tone=data.get('tone'),
        image_count=len(data.get('images', []))
    )

    # 非同期タスクをキュー
    task = auto_post_blog_task.delay(
        user_id=request.user.id,
        title=content['title'],
        body=content['body'],
        image_paths=data.get('images', []),
        stylist_id=data.get('stylist_id'),
        coupon_name=data.get('coupon_name')
    )

    return JsonResponse({
        'task_id': task.id,
        'status': 'queued',
        'title': content['title']
    })
```

### 4.7 タスクステータス確認

```python
@login_required
def check_task_status(request, task_id):
    """
    タスクの実行状況を確認
    """
    from celery.result import AsyncResult

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

### 4.8 Workerの起動

```bash
# 開発環境
celery -A config worker -l info

# 本番環境（並行数制限）
celery -A config worker -l info --concurrency=2

# Beatスケジューラー
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 4.9 Docker Compose設定

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=2
    volumes:
      - .:/app
      - ./media:/app/media
    depends_on:
      - redis
      - db
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings
    shm_size: '2gb'  # Playwright用

  celery_beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
    depends_on:
      - redis
      - db

volumes:
  redis_data:
```

---

## 5. Playwright自動化統合

### 5.1 自動化クラスの実装

```python
# apps/blog/automation.py
from playwright.sync_api import Playwright, Browser, Page, TimeoutError as PlaywrightTimeout
import logging
import time

logger = logging.getLogger(__name__)

class SalonBoardAutomation:
    """
    SALON BOARD自動操作クラス
    """

    def __init__(self, playwright: Playwright, login_id: str, password: str):
        self.p = playwright
        self.login_id = login_id
        self.password = password
        self.browser = None
        self.page = None

    def post_blog(
        self,
        salon_id: str,
        title: str,
        body: str,
        image_paths: list,
        stylist_id: str,
        coupon_name: str
    ) -> dict:
        """
        ブログを自動投稿
        """
        try:
            # ブラウザ起動
            self.browser = self.p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = context.new_page()
            self.page.set_default_timeout(60000)  # 60秒

            # ログイン
            self._login()

            # 店舗選択
            if self._is_multi_salon_page():
                self._select_salon(salon_id)

            # ブログ投稿画面へ遷移
            self._navigate_to_blog_form()

            # フォーム入力
            self._fill_blog_form(
                title=title,
                body=body,
                image_paths=image_paths,
                stylist_id=stylist_id,
                coupon_name=coupon_name
            )

            # 確認画面へ
            self.page.click('a#confirm')
            time.sleep(2)

            # 登録・反映
            self.page.click('a#reflect')
            time.sleep(3)

            # スクリーンショット
            screenshot_path = f"media/screenshots/{int(time.time())}.png"
            self.page.screenshot(path=screenshot_path, full_page=True)

            return {
                'status': 'success',
                'screenshot_path': screenshot_path
            }

        except Exception as e:
            logger.error(f"Automation failed: {e}")
            if self.page:
                error_screenshot = f"media/errors/{int(time.time())}.png"
                self.page.screenshot(path=error_screenshot)
            raise

        finally:
            if self.browser:
                self.browser.close()

    def _login(self):
        """ログイン処理"""
        self.page.goto("https://salonboard.com/login/")
        self._remove_blockers()
        self._check_robot_detection()

        self.page.fill("input[name='userId']", self.login_id)
        self.page.fill("#jsiPwInput", self.password)
        self.page.click("#idPasswordInputForm > div > div > a")
        self.page.wait_for_load_state('networkidle')

        self._check_robot_detection()

    def _is_multi_salon_page(self) -> bool:
        """複数店舗選択画面かどうか"""
        return self.page.is_visible("#biyouStoreInfoArea")

    def _select_salon(self, salon_id: str):
        """店舗選択"""
        selector = f"a[id='{salon_id}']"
        if self.page.is_visible(selector):
            self.page.click(selector)
            self.page.wait_for_load_state('networkidle')
        else:
            raise ValueError(f"Salon {salon_id} not found")

    def _navigate_to_blog_form(self):
        """ブログ投稿画面へ遷移"""
        # 掲載管理
        self.page.click("#globalNavi > ul.common-CLPcommon__globalNavi > li:nth-child(2) > a")
        time.sleep(1)

        # ブログ
        self.page.click("#cmsForm > div > div > ul > li:nth-child(9) > a")
        time.sleep(1)

        # 新規投稿
        self.page.click("#newPosts")
        self.page.wait_for_load_state('networkidle')

    def _fill_blog_form(
        self,
        title: str,
        body: str,
        image_paths: list,
        stylist_id: str,
        coupon_name: str
    ):
        """フォーム入力"""
        # タイトル
        self.page.fill("input#blogTitle", title)

        # カテゴリ
        self.page.select_option("select#blogCategoryCd", "BL02")

        # スタイリスト
        if stylist_id:
            self.page.select_option("select#stylistId", stylist_id)

        # クーポン選択
        if coupon_name:
            self._select_coupon(coupon_name)

        # 本文と画像
        self._insert_content_with_images(body, image_paths)

    def _select_coupon(self, coupon_name: str):
        """クーポン選択"""
        self.page.click("a.jsc_SB_modal_trigger")
        time.sleep(1)

        # 部分一致検索
        self.page.locator("div#couponWrap label").filter(
            has_text=coupon_name
        ).first.click()

        self.page.click("a.jsc_SB_modal_setting_btn")
        time.sleep(1)

    def _insert_content_with_images(self, body: str, image_paths: list):
        """
        本文と画像を交互に挿入（nicEditor API + contenteditable）
        """
        editor_div = self.page.locator("div.nicEdit-main[contenteditable='true']")
        editor_div.evaluate("el => el.innerHTML = ''")

        # nicEditor API（textarea#blogContents）を優先的に利用
        nic_editor_available = self.page.evaluate("""
            () => {
                try {
                    return !!nicEditors.findEditor('blogContents');
                } catch (e) {
                    return false;
                }
            }
        """)

        import re
        parts = re.split(r'(\{\{image_\d+\}\})', body)

        for part in parts:
            if part.startswith('{{image_'):
                match = re.match(r'\{\{image_(\d+)\}\}', part)
                if match:
                    img_num = int(match.group(1)) - 1
                    if img_num < len(image_paths):
                        self._upload_image(editor_div, image_paths[img_num])
            else:
                if part.strip():
                    if nic_editor_available:
                        escaped = part.replace('`', '\\`').replace('${', '\\${')
                        self.page.evaluate(f"""
                            () => {{
                                const editor = nicEditors.findEditor('blogContents');
                                if (!editor) return;
                                const current = editor.getContent();
                                editor.setContent(current + `{escaped}`);
                            }}
                        """)
                    else:
                        editor_div.evaluate(f"el => el.innerHTML += '{part}'")
                    self._move_cursor_to_end(editor_div)

    def _upload_image(self, editor_div, image_path: str):
        """画像アップロード"""
        # カーソルを末尾へ
        self._move_cursor_to_end(editor_div)

        # アップロードボタン
        self.page.click("a#upload")
        time.sleep(1)

        # ファイル選択
        self.page.set_input_files("input#sendFile", image_path)

        # サムネイル待機
        self.page.wait_for_selector("img.imageUploaderModalThumbnail", timeout=30000)

        # 送信
        self.page.click("input.imageUploaderModalSubmitButton.isActive")

        # モーダル消失待機
        self.page.wait_for_selector("div.imageUploaderModal", state="hidden")
        time.sleep(1)

        # カーソルを再び末尾へ
        self._move_cursor_to_end(editor_div)

    def _move_cursor_to_end(self, editor_body):
        """カーソルを末尾へ移動（contenteditable div 対象）"""
        js_code = """
        (body) => {
            const doc = body.ownerDocument;
            const win = doc.defaultView || doc.parentWindow;

            body.focus();
            const range = doc.createRange();
            const selection = win.getSelection();

            range.selectNodeContents(body);
            range.collapse(false);

            selection.removeAllRanges();
            selection.addRange(range);
        }
        """
        editor_body.evaluate(js_code)

    def _remove_blockers(self):
        """妨害要素を非表示"""
        css = """
        .karte-widget__container,
        [class*='_reception-Skin'],
        [class*='_reception-MinimumWidget'],
        [id^='karte-'] {
            display: none !important;
        }
        """
        self.page.add_style_tag(content=css)

    def _check_robot_detection(self):
        """ロボット検知チェック"""
        robot_selectors = [
            "iframe[src*='recaptcha']",
            "div.g-recaptcha",
            "img[alt*='認証']"
        ]

        for selector in robot_selectors:
            if self.page.is_visible(selector):
                raise Exception("Robot detection triggered (CAPTCHA)")
```

---

## 6. Django Channels (WebSocket) 統合

### 6.1 概要
リアルタイムでタスクの進捗をユーザーに通知するため、Django Channelsを使用してWebSocket通信を実装します。

### 6.2 インストールと設定

```bash
pip install channels channels-redis daphne
```

### 6.3 Django設定

```python
# config/settings.py

INSTALLED_APPS = [
    'daphne',  # 最上部に配置
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
    'channels',
    # ...
]

# ASGI設定
ASGI_APPLICATION = 'config.asgi.application'

# Channelsレイヤー設定（Redisバックエンド）
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.environ.get('REDIS_HOST', 'localhost'), 6379)],
        },
    },
}
```

### 6.4 ASGI設定

```python
# config/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

# WebSocketルーティングのインポート
from apps.blog import routing as blog_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                blog_routing.websocket_urlpatterns
            )
        )
    ),
})
```

### 6.5 WebSocketコンシューマー

```python
# apps/blog/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class BlogProgressConsumer(AsyncWebsocketConsumer):
    """
    ブログ投稿進捗をリアルタイムで通知するコンシューマー
    """

    async def connect(self):
        """WebSocket接続時"""
        self.user = self.scope["user"]

        if self.user == AnonymousUser():
            await self.close()
            return

        # ユーザー専用のグループに参加
        self.group_name = f'user_{self.user.id}_progress'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # 接続成功メッセージ
        await self.send(text_data=json.dumps({
            'type': 'connection',
            'message': 'WebSocket connected'
        }))

    async def disconnect(self, close_code):
        """WebSocket切断時"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """クライアントからのメッセージ受信（オプション）"""
        pass

    async def task_progress(self, event):
        """
        Celeryタスクからの進捗メッセージを送信
        """
        await self.send(text_data=json.dumps({
            'type': 'task_progress',
            'task_id': event['task_id'],
            'status': event['status'],
            'progress': event.get('progress', 0),
            'message': event.get('message', ''),
            'data': event.get('data', {})
        }))

    async def task_error(self, event):
        """
        エラー通知を送信
        """
        await self.send(text_data=json.dumps({
            'type': 'task_error',
            'task_id': event['task_id'],
            'error': event['error'],
            'message': event.get('message', '')
        }))
```

### 6.6 WebSocketルーティング

```python
# apps/blog/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/blog/progress/', consumers.BlogProgressConsumer.as_asgi()),
]
```

### 6.7 CeleryタスクからWebSocket通知

```python
# apps/blog/tasks.py
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

def send_progress(user_id: int, task_id: str, status: str, progress: int, message: str, data: dict = None):
    """
    WebSocket経由で進捗を通知
    """
    channel_layer = get_channel_layer()
    group_name = f'user_{user_id}_progress'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'task_progress',
            'task_id': task_id,
            'status': status,
            'progress': progress,
            'message': message,
            'data': data or {}
        }
    )

def send_error(user_id: int, task_id: str, error: str, message: str = ''):
    """
    WebSocket経由でエラーを通知
    """
    channel_layer = get_channel_layer()
    group_name = f'user_{user_id}_progress'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'task_error',
            'task_id': task_id,
            'error': error,
            'message': message
        }
    )

@shared_task(bind=True, max_retries=3)
def generate_blog_content_task(self, post_id: int):
    """
    AI記事3案生成タスク

    生成完了後、BlogPostのステータスを'selecting'に変更し、
    ユーザーが3案から選択する画面へ誘導する。
    """
    task_id = self.request.id

    try:
        from apps.blog.models import BlogPost
        from apps.blog.gemini_client import GeminiClient

        post = BlogPost.objects.get(id=post_id)
        user_id = post.user_id

        # 1. タスク開始通知
        send_progress(user_id, task_id, 'started', 10, 'AI記事生成を開始しました')

        # 2. プロンプト構築
        gemini_client = GeminiClient()
        image_count = post.images.count()

        full_prompt = f"""キーワード: {post.keywords}
トーン: {post.tone or 'friendly'}"""

        # 3. AI生成（3案）
        send_progress(user_id, task_id, 'generating', 30, 'AIが3つの記事案を生成中...')
        
        result = gemini_client.generate_blog_content_variations(
            prompt=full_prompt,
            num_variations=3,
            image_count=image_count,
        )

        # 4. 結果保存
        send_progress(user_id, task_id, 'saving', 80, '生成完了。データベースを更新中...')
        
        post.generated_variations = result['variations']
        post.ai_generated = True
        post.status = 'selecting'  # ユーザーが選択する状態へ
        post.save()

        # 5. 完了通知
        send_progress(
            user_id,
            task_id,
            'completed',
            100,
            '3つの記事案が生成されました。選択画面に移動します。',
            {'redirect_url': f'/blog/posts/{post_id}/select/'}
        )

        return {
            'success': True,
            'post_id': post_id,
            'variation_count': len(result['variations']),
        }

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        send_error(user_id, task_id, str(exc), 'AI生成中にエラーが発生しました')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def publish_to_salon_board_task(self, post_id: int):
    """
    SALON BOARDへの自動投稿タスク
    """
    task_id = self.request.id

    try:
        from apps.blog.models import BlogPost
        from apps.accounts.models import User
        from playwright.sync_api import sync_playwright
        from apps.blog.salon_board_client import SalonBoardClient

        post = BlogPost.objects.get(id=post_id)
        user = post.user
        user_id = user.id

        # 1. タスク開始通知
        send_progress(user_id, task_id, 'started', 10, '投稿処理を開始しました')

        # 2. 認証情報取得
        from apps.accounts.utils import decrypt_credential
        sb_account = user.salon_board_account
        login_id, password = sb_account.get_credentials()

        # 3. 自動投稿開始
        send_progress(user_id, task_id, 'posting', 50, 'SALON BOARDにログイン中...')

        with sync_playwright() as p:
            client = SalonBoardClient(p, login_id, password)
            
            send_progress(user_id, task_id, 'posting', 70, 'ブログを投稿中...')

            result = client.post_blog(
                salon_id=user.hpb_salon_id,
                title=post.title,
                body=post.content,
                image_paths=[img.image_file.path for img in post.images.all()],
                stylist_id=post.stylist_id,
                coupon_name=post.coupon_name
            )

        # 4. 完了通知
        send_progress(user_id, task_id, 'completed', 100, '投稿が完了しました！')

        return {
            'status': 'success',
            'screenshot_path': result.get('screenshot_path')
        }

    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        send_error(user_id, task_id, str(exc), '投稿中にエラーが発生しました')
        raise self.retry(exc=exc, countdown=60)
```

### 6.8 フロントエンド実装（JavaScript）

```html
<!-- templates/blog/create.html -->
<div id="progress-container" class="hidden">
    <div class="progress-bar">
        <div id="progress-bar-fill" class="progress-bar-fill" style="width: 0%"></div>
    </div>
    <p id="progress-message" class="text-sm text-gray-600 mt-2"></p>
</div>

<div id="error-container" class="hidden bg-red-100 border border-red-400 p-4 rounded">
    <p id="error-message" class="text-red-700"></p>
</div>

<script>
// WebSocket接続
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/blog/progress/`;
const socket = new WebSocket(wsUrl);

socket.onopen = function(e) {
    console.log('WebSocket connection established');
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);

    if (data.type === 'task_progress') {
        // 進捗表示を更新
        document.getElementById('progress-container').classList.remove('hidden');
        document.getElementById('progress-bar-fill').style.width = data.progress + '%';
        document.getElementById('progress-message').textContent = data.message;

        // 完了時の処理
        if (data.status === 'completed') {
            setTimeout(() => {
                window.location.href = '/blog/list/';
            }, 2000);
        }
    } else if (data.type === 'task_error') {
        // エラー表示
        document.getElementById('error-container').classList.remove('hidden');
        document.getElementById('error-message').textContent = data.message || data.error;
        document.getElementById('progress-container').classList.add('hidden');
    }
};

socket.onerror = function(error) {
    console.error('WebSocket error:', error);
};

socket.onclose = function(event) {
    console.log('WebSocket connection closed');
};

// フォーム送信時
document.getElementById('blog-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const formData = new FormData(this);

    try {
        const response = await fetch('/api/blog/create/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });

        const data = await response.json();

        if (response.ok) {
            // タスクが開始されたので、WebSocketで進捗を待つ
            console.log('Task started:', data.task_id);
        } else {
            alert('エラー: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('送信に失敗しました');
    }
});
</script>
```

### 6.9 Docker Compose設定

```yaml
# docker-compose.yml
services:
  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    depends_on:
      - redis
      - db

  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=2
    volumes:
      - .:/app
      - ./media:/app/media
    depends_on:
      - redis
      - db
    shm_size: '2gb'

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

---

## 7. 統合テスト戦略

### 7.1 単体テスト

```python
# tests/test_gemini_integration.py
import pytest
from apps.blog.ai_generator import generate_blog_content

def test_generate_blog_content():
    result = generate_blog_content(
        keywords="カット カラー",
        tone="親しみやすい",
        image_count=2
    )

    assert 'title' in result
    assert len(result['title']) <= 25
    assert 'body' in result
    assert '{{image_1}}' in result['body']
```

### 7.2 統合テスト

```python
# tests/test_full_workflow.py
import pytest
from django.test import TestCase
from apps.blog.tasks import auto_post_blog_task

class FullWorkflowTest(TestCase):
    def test_end_to_end_blog_posting(self):
        """
        記事生成→自動投稿の統合テスト
        """
        # TODO: 実装
        pass
```

---

## 8. パフォーマンス最適化

### 8.1 Gemini API
- **キャッシング**: 頻繁に使われるプロンプトテンプレートをキャッシュ
- **バッチ処理**: 複数記事を一度に生成する場合は並列化

### 8.2 Celery
- **Concurrency制限**: Playwright使用時は `--concurrency=2`
- **タイムアウト設定**: `CELERY_TASK_TIME_LIMIT = 30 * 60`

### 8.3 Playwright
- **ヘッドレスモード**: 本番は必ず `headless=True`
- **共有メモリ**: Docker の `shm_size: '2gb'`

### 8.4 WebSocket最適化
- **接続プール**: 複数ユーザー同時接続時のRedis接続管理
- **メッセージサイズ**: 大きなデータは送信せず、必要最小限の情報のみ
- **切断時の再接続**: フロントエンドで自動再接続ロジックを実装

---

## 9. セキュリティ考慮事項

### 9.1 認証情報の保護
- SALON BOARD認証情報は**必ず暗号化**して保存
- Fernet (cryptography) を使用
- 環境変数 `ENCRYPTION_KEY` の厳重管理

### 9.2 APIキーの管理
- `.env` ファイルをGit管理外に
- 環境変数経由で読み込み
- Docker Secretsの使用検討

### 9.3 CSRF/XSS対策
- DjangoのCSRF保護を有効化
- Supabaseからのレスポンスをサニタイズ
- WebSocket通信も認証必須

### 9.4 WebSocketセキュリティ
- AllowedHostsOriginValidatorで接続元を制限
- 認証済みユーザーのみ接続許可
- ユーザー専用グループで情報漏洩防止

---

## 10. 監視とロギング

### 10.1 ログ設定

```python
# config/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'apps': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
    },
}
```

### 10.2 Celery監視

```bash
# Flower (Celeryモニタリングツール)
pip install flower
celery -A config flower --port=5555
```

---

## 11. 参考資料

### 公式ドキュメント
- [Google Gemini Python SDK](https://github.com/googleapis/python-genai)
- [Supabase Python Client](https://github.com/supabase/supabase-py)
- [Django Celery Documentation](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html)
- [Playwright Python](https://playwright.dev/python/)
- [Django Channels Documentation](https://channels.readthedocs.io/)

### 統合ガイド
- [Django Supabase Integration Guide](https://bootstrapped.app/guide/how-to-use-supabase-with-django)
- [Asynchronous Tasks With Django and Celery](https://realpython.com/asynchronous-tasks-with-django-and-celery/)
- [Django Celery Redis Integration](https://testdriven.io/guides/django-celery/)

### トラブルシューティング
- [Playwright + Celery Issues](https://github.com/microsoft/playwright-python/issues/1995)
- [Stack Overflow: Celery Playwright Import](https://stackoverflow.com/questions/76103950/cannot-run-celery-worker-while-importing-playwright-library)

---

## 12. 次のステップ

このドキュメントを元に、以下の実装ドキュメントを作成します：

1. **05_project_structure.md** - プロジェクト構造とディレクトリ設計
2. **06_database_schema.md** - データベース設計詳細
3. **07_api_endpoints.md** - APIエンドポイント仕様
4. **08_deployment_guide.md** - デプロイ手順とCI/CD設定

---

**作成日**: 2025年1月
**最終更新**: 2025年11月
**ステータス**: AI3案生成、画像プレースホルダー保証機能対応
