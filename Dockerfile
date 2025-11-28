FROM python:3.12-slim

# システム依存パッケージのインストール
# fonts-noto-cjk: 日本語フォント (Playwright用、必須)
# chromium依存パッケージ: Playwright用
# nodejs + npm: Tailwind CSS ビルド用
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
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    git \
    postgresql-client \
    curl \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリ設定
WORKDIR /app

# Python依存パッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Playwright ブラウザバイナリのインストール
RUN playwright install chromium
# playwright install-depsは古いパッケージ名を参照するため手動インストール
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    fonts-liberation \
    fonts-unifont \
    libu2f-udev \
    libvulkan1 \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# アプリケーションコードをコピー
COPY . .

# npm依存関係インストール & Tailwind CSSビルド
RUN npm install && npm run build:css

# 静的ファイルディレクトリ作成
RUN mkdir -p /app/staticfiles /app/media /app/logs

# 静的ファイル収集（本番用、エラーは無視）
RUN python manage.py collectstatic --noinput --clear 2>/dev/null || true

# ポート公開
EXPOSE 8000

# デフォルトコマンド（docker-compose.ymlで上書き可能）
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "--access-logfile", "-"]
