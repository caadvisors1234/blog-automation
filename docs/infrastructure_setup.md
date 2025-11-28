# 03. インフラ・環境構築ガイド (Infrastructure Setup)

## 1. 概要
本システムは Docker および Docker Compose 上で動作する。Playwright ブラウザコンテナでは **日本語フォント対応** が必須要件となる（スクリーンショットの文字化け防止のため）。

### Compose ネットワーク/ポート方針（2025-XX 更新）
- ベース `docker-compose.yml` は **ポートを公開しない**（NPM 経由でアクセス）。
- 共有ネットワーク名: `app-network`（Nginx Proxy Manager などと同一ネットワークで運用）。
- ローカル開発時のみ `docker-compose.override.yml` でポートを公開（例: `18001:8000`）。
- `db` / `redis` は内部ネットワーク `internal` のみ。`web`/`flower` は `internal` + `app-network` に参加。

### 本番アプリサーバ
- `gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000`
- 静的配信: WhiteNoise (`CompressedManifestStaticFilesStorage`)
- collectstatic はイメージビルドで実行済み。

## 2. Dockerfile 設計 (Web/Worker共通)

Python 3.12 ベースのイメージを使用し、Playwright 依存関係と日本語フォントをインストールする。

```dockerfile
FROM python:3.12-slim

# システム依存パッケージのインストール
# fonts-noto-cjk: 日本語フォント (必須)
# chromium 依存パッケージ: Playwright用
RUN apt-get update && apt-get install -y \\
    fonts-noto-cjk \\
    libnss3 \\
    libnspr4 \\
    libatk1.0-0 \\
    libatk-bridge2.0-0 \\
    libcups2 \\
    libdrm2 \\
    libxkbcommon0 \\
    libxcomposite1 \\
    libxdamage1 \\
    libxfixes3 \\
    libxrandr2 \\
    libgbm1 \\
    libasound2 \\
    git \\
    && apt-get clean \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ブラウザバイナリのインストール
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

# 実行コマンドは docker-compose.yml で定義
```
## 3. 環境変数 (.env)

セキュリティ情報は `.env` ファイルで管理し、Gitには含めない。

```
# Django Settings
DEBUG=False
SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,your-vps-ip

# Database
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=secure_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis (Celery Broker)
REDIS_URL=redis://redis:6379/0

# Supabase (Auth)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Encryption Key (for saving ID/PASS)
# cryptography.fernet.Fernet.generate_key() で生成
ENCRYPTION_KEY=your-fernet-key

```

## 4. Playwright 実行時の注意点 (Celery Worker)

### メモリリソース管理

ブラウザ起動はメモリを消費するため、Celery Worker の同時実行数（Concurrency）を制限することを推奨する。

**docker-compose.yml 例:**

```yaml
services:
  celery_worker:
    build: .
    command: celery -A config worker -l info --concurrency=2
    volumes:
      - .:/app
      - ./media:/app/media  # 画像保存用
    depends_on:
      - redis
      - db
    # 共有メモリサイズを増やす（ブラウザクラッシュ防止）
    shm_size: '2gb'

```

### タイムアウト設定

画像アップロードやページ遷移は回線状況により時間がかかる場合があるため、Playwright のデフォルトタイムアウト（通常30秒）を **60秒** 程度に緩和して初期化することを推奨する。

```python
context = browser.new_context()
page = context.new_page()
page.set_default_timeout(60000) # 60秒

```
