# 05. プロジェクト構造設計書 (Project Structure Design)

## 1. 概要
本ドキュメントは、HPBブログ自動化システムのプロジェクト構造、ディレクトリ構成、およびDjangoアプリケーション分割を定義します。

---

## 2. プロジェクトルート構成

```
blog-automation/
├── .env                      # 環境変数（Git管理外）
├── .env.example              # 環境変数テンプレート
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt          # Python依存パッケージ
├── requirements-dev.txt      # 開発用パッケージ
├── manage.py
├── pytest.ini               # テスト設定
├── README.md
│
├── config/                  # Django設定ディレクトリ
│   ├── __init__.py
│   ├── settings.py          # メイン設定ファイル
│   ├── settings/            # 環境別設定（オプション）
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py              # ルートURLconf
│   ├── asgi.py              # ASGI設定（Django Channels用）
│   ├── wsgi.py              # WSGI設定
│   └── celery.py            # Celery設定
│
├── apps/                    # Djangoアプリケーション
│   ├── accounts/            # ユーザー管理・認証
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── backends.py      # Supabase認証バックエンド
│   │   ├── forms.py
│   │   ├── middleware.py    # 認証ミドルウェア
│   │   ├── models.py        # Userモデル
│   │   ├── urls.py
│   │   ├── utils.py         # 暗号化ユーティリティ
│   │   ├── views.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       └── test_views.py
│   │
│   ├── blog/                # ブログ投稿機能
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py        # BlogPost, BlogImage等
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tasks.py         # Celeryタスク
│   │   ├── consumers.py     # WebSocketコンシューマー
│   │   ├── routing.py       # WebSocketルーティング
│   │   ├── ai_generator.py  # Gemini統合
│   │   ├── scraper.py       # HPBスクレイピング
│   │   ├── automation.py    # Playwright自動化
│   │   ├── selectors.py     # セレクタ定義
│   │   ├── exceptions.py    # カスタム例外
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_views.py
│   │       ├── test_tasks.py
│   │       ├── test_ai_generator.py
│   │       └── test_automation.py
│   │
│   └── core/                # 共通機能
│       ├── __init__.py
│       ├── management/      # カスタムコマンド
│       │   ├── __init__.py
│       │   └── commands/
│       │       ├── __init__.py
│       │       └── seed_data.py
│       ├── middleware.py    # 共通ミドルウェア
│       ├── templatetags/    # カスタムテンプレートタグ
│       │   ├── __init__.py
│       │   └── custom_filters.py
│       └── utils.py         # 共通ユーティリティ
│
├── templates/               # Djangoテンプレート
│   ├── base.html           # ベーステンプレート
│   ├── includes/           # 再利用可能なパーツ
│   │   ├── header.html
│   │   ├── footer.html
│   │   ├── messages.html
│   │   └── progress_bar.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── settings.html
│   ├── blog/
│   │   ├── list.html       # 投稿一覧
│   │   ├── create.html     # 新規作成
│   │   ├── detail.html     # 投稿詳細
│   │   └── history.html    # 投稿履歴
│   └── errors/
│       ├── 404.html
│       ├── 500.html
│       └── 503.html
│
├── static/                 # 静的ファイル
│   ├── css/
│   │   ├── tailwind.css    # Tailwind CSS
│   │   └── custom.css      # カスタムスタイル
│   ├── js/
│   │   ├── websocket.js    # WebSocket処理
│   │   ├── form-validation.js
│   │   └── image-preview.js
│   └── images/
│       └── logo.png
│
├── media/                  # アップロードファイル
│   ├── blog_images/        # ブログ画像
│   ├── screenshots/        # 投稿完了スクリーンショット
│   └── errors/             # エラー時のスクリーンショット
│
├── logs/                   # ログファイル
│   ├── app.log
│   ├── celery.log
│   └── error.log
│
├── tests/                  # 統合テスト
│   ├── __init__.py
│   ├── conftest.py         # pytestフィクスチャ
│   ├── test_integration.py
│   └── fixtures/
│       └── test_data.json
│
└── docs/                   # ドキュメント
    ├── system_requirements.md
    ├── playwright_automation_spec.md
    ├── infrastructure_setup.md
    ├── technical_integration_guide.md
    ├── project_structure.md          # 本ドキュメント
    ├── database_schema.md
    ├── api_endpoints.md
    └── frontend_design.md
```

---

## 3. アプリケーション分割の方針

### 3.1 accounts（ユーザー管理）
**責務**:
- Supabase認証との統合
- ユーザー情報管理
- SALON BOARD認証情報の暗号化保存
- HPBサロン設定管理

**主要モデル**:
- `User`: 拡張ユーザーモデル

### 3.2 blog（ブログ投稿）
**責務**:
- ブログ記事の生成（Gemini統合）
- 画像管理
- 自動投稿（Playwright統合）
- スクレイピング（マスタデータ取得）
- 投稿履歴管理
- WebSocketでのリアルタイム進捗通知

**主要モデル**:
- `BlogPost`: 投稿記事
- `BlogImage`: 画像
- `PostLog`: 投稿ログ
- `StylistMaster`: スタイリスト情報（キャッシュ用、オプション）
- `CouponMaster`: クーポン情報（キャッシュ用、オプション）

### 3.3 core（共通機能）
**責務**:
- 全アプリ共通のユーティリティ
- カスタムテンプレートタグ・フィルタ
- 管理コマンド

---

## 4. 設定ファイルの構成

### 4.1 requirements.txt

```txt
# Django
Django==5.0.0
django-environ==0.11.2

# Database
psycopg2-binary==2.9.9

# Async & WebSocket
daphne==4.0.0
channels==4.0.0
channels-redis==4.1.0

# Celery & Redis
celery==5.3.4
redis==5.0.1
django-celery-results==2.5.1
django-celery-beat==2.5.0

# Authentication
supabase==2.3.0
PyJWT==2.8.0
cryptography==41.0.7

# AI & Scraping
google-genai==0.2.0
beautifulsoup4==4.12.2
lxml==4.9.4

# Browser Automation
playwright==1.40.0

# Utilities
python-dotenv==1.0.0
Pillow==10.1.0
```

### 4.2 requirements-dev.txt

```txt
-r requirements.txt

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
pytest-asyncio==0.21.1
factory-boy==3.3.0

# Code Quality
black==23.12.1
flake8==7.0.0
isort==5.13.2
mypy==1.7.1

# Monitoring
flower==2.0.1
django-debug-toolbar==4.2.0
```

### 4.3 .env.example

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
POSTGRES_DB=blog_automation_db
POSTGRES_USER=blog_automation_user
POSTGRES_PASSWORD=strong-password-here
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret

# Google Gemini
GEMINI_API_KEY=your-gemini-api-key

# Encryption
ENCRYPTION_KEY=your-fernet-key-here

# Email (Optional, for future)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Logging
LOG_LEVEL=INFO
```

### 4.4 Dockerfile

```dockerfile
FROM python:3.12-slim

# システム依存パッケージ
RUN apt-get update && apt-get install -y \
    fonts-noto-cjk \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    git \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ブラウザ
RUN playwright install chromium
RUN playwright install-deps chromium

# アプリケーションコード
COPY . .

# 静的ファイル収集（本番用）
RUN python manage.py collectstatic --noinput || true

# ポート公開
EXPOSE 8000

# デフォルトコマンド（docker-compose.ymlで上書き）
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
```

### 4.5 docker-compose.yml

```yaml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    command: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    volumes:
      - .:/app
      - ./media:/app/media
      - ./logs:/app/logs
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=2
    volumes:
      - .:/app
      - ./media:/app/media
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - redis
      - db
    shm_size: '2gb'
    deploy:
      resources:
        limits:
          memory: 4G

  celery_beat:
    build: .
    command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    volumes:
      - .:/app
      - ./logs:/app/logs
    env_file:
      - .env
    depends_on:
      - redis
      - db

  flower:
    build: .
    command: celery -A config flower --port=5555
    volumes:
      - .:/app
    ports:
      - "5555:5555"
    env_file:
      - .env
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

---

## 5. ファイル命名規則

### 5.1 Pythonファイル
- **モデル**: `models.py` - 単一モデルでも複数モデルでも
- **ビュー**: `views.py` - 関数ベースまたはクラスベース
- **URL設定**: `urls.py`
- **フォーム**: `forms.py`
- **タスク**: `tasks.py` - Celeryタスク
- **ユーティリティ**: `utils.py` - 汎用関数
- **例外**: `exceptions.py` - カスタム例外クラス

### 5.2 テンプレート
- **スネークケース**: `blog_list.html`、`create_post.html`
- **パーシャル**: `_form.html`、`_sidebar.html`（アンダースコアで開始）

### 5.3 静的ファイル
- **CSS**: `kebab-case.css` （例: `custom-styles.css`）
- **JavaScript**: `kebab-case.js` （例: `form-validation.js`）

---

## 6. import順序規則

```python
# 1. 標準ライブラリ
import os
import sys
from datetime import datetime

# 2. サードパーティライブラリ
from django.db import models
from django.contrib.auth import get_user_model
from celery import shared_task

# 3. ローカルアプリケーション
from apps.accounts.models import User
from apps.blog.utils import encrypt_data
from config.settings import MEDIA_ROOT
```

---

## 7. コーディング規約

### 7.1 命名規則
- **クラス名**: PascalCase （例: `BlogPost`, `UserProfile`）
- **関数・変数**: snake_case （例: `get_user_posts`, `user_id`）
- **定数**: UPPER_SNAKE_CASE （例: `MAX_IMAGE_SIZE`, `DEFAULT_TIMEOUT`）
- **プライベート**: `_`で開始 （例: `_internal_method`）

### 7.2 docstring
```python
def generate_blog_content(keywords: str, tone: str, image_count: int) -> dict:
    """
    Gemini APIを使用してブログコンテンツを生成する

    Args:
        keywords (str): キーワード
        tone (str): トーン＆マナー
        image_count (int): 画像枚数

    Returns:
        dict: {"title": str, "body": str, "usage": int}

    Raises:
        ValueError: キーワードが空の場合
        APIError: Gemini API呼び出し失敗時
    """
    pass
```

### 7.3 型ヒント
```python
from typing import List, Dict, Optional

def scrape_stylists(salon_url: str) -> List[Dict[str, str]]:
    """スタイリスト情報をスクレイピング"""
    pass

def get_user_blog_posts(user_id: int, limit: Optional[int] = None) -> List['BlogPost']:
    """ユーザーのブログ投稿を取得"""
    pass
```

---

## 8. テスト構成

### 8.1 単体テスト
```python
# apps/blog/tests/test_ai_generator.py
import pytest
from apps.blog.ai_generator import generate_blog_content

@pytest.mark.django_db
class TestAIGenerator:
    def test_generate_blog_content_success(self):
        result = generate_blog_content(
            keywords="カット カラー",
            tone="親しみやすい",
            image_count=2
        )
        assert 'title' in result
        assert len(result['title']) <= 25
        assert 'body' in result
```

### 8.2 統合テスト
```python
# tests/test_integration.py
import pytest
from django.test import Client

@pytest.mark.django_db
class TestBlogWorkflow:
    def test_full_blog_posting_workflow(self):
        client = Client()
        # ログイン
        # 画像アップロード
        # ブログ作成
        # 自動投稿タスク起動
        # 完了確認
        pass
```

---

## 9. ログ設定

### 9.1 ログレベル
- **DEBUG**: 開発時の詳細情報
- **INFO**: 一般的な情報（タスク開始・完了等）
- **WARNING**: 警告（リトライ発生等）
- **ERROR**: エラー（処理失敗）
- **CRITICAL**: 重大なエラー

### 9.2 ログ出力先
```python
# apps/blog/tasks.py
import logging

logger = logging.getLogger(__name__)  # 'apps.blog.tasks'

@shared_task
def auto_post_blog_task(...):
    logger.info(f"Starting blog post task for user {user_id}")
    try:
        # 処理
        logger.info(f"Blog post completed successfully")
    except Exception as e:
        logger.error(f"Blog post failed: {e}", exc_info=True)
        raise
```

---

## 10. Git管理外ファイル (.gitignore)

```gitignore
# Environment
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Django
*.log
db.sqlite3
/media
/staticfiles
/logs

# Celery
celerybeat-schedule
celerybeat.pid

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml

# Testing
.coverage
htmlcov/
.pytest_cache/

# Playwright
playwright-report/
test-results/
```

---

## 11. 開発ワークフロー

### 11.1 初期セットアップ
```bash
# 1. リポジトリクローン
git clone <repository-url>
cd blog-automation

# 2. 環境変数設定
cp .env.example .env
# .envを編集

# 3. Docker起動
docker-compose up -d --build

# 4. マイグレーション
docker-compose exec web python manage.py migrate

# 5. 管理ユーザー作成
docker-compose exec web python manage.py createsuperuser

# 6. Playwrightブラウザインストール確認
docker-compose exec celery_worker playwright install chromium
```

### 11.2 日常の開発
```bash
# サービス起動
docker-compose up

# ログ確認
docker-compose logs -f web
docker-compose logs -f celery_worker

# テスト実行
docker-compose exec web pytest

# マイグレーション作成
docker-compose exec web python manage.py makemigrations

# 静的ファイル収集
docker-compose exec web python manage.py collectstatic

# シェルアクセス
docker-compose exec web python manage.py shell
```

---

## 12. パフォーマンス考慮事項

### 12.1 静的ファイル
- 本番環境ではNginxなどで配信
- Tailwind CSSはプロダクションビルド使用

### 12.2 メディアファイル
- 画像は `/media/blog_images/` に保存
- 定期的な古いファイルのクリーンアップ

### 12.3 ログローテーション
- `RotatingFileHandler`で10MBごとにローテーション
- 5世代まで保持

---

## 13. まとめ

このプロジェクト構造により：
- **明確な責務分離**: アプリごとに役割が明確
- **スケーラビリティ**: 機能追加が容易
- **テスト可能性**: 各コンポーネントを独立してテスト
- **保守性**: 一貫した命名規則とディレクトリ構成

次のステップでは、この構造を基にデータベーススキーマを詳細設計します。

---

**作成日**: 2025年1月
**最終更新**: 2025年1月
**ステータス**: 初版完成
