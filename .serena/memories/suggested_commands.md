# 開発用コマンド

## 環境構築
```bash
# Docker環境起動
docker-compose up -d --build

# または venv環境
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## 開発コマンド
```bash
# マイグレーション
python manage.py migrate

# サーバー起動
python manage.py runserver

# スーパーユーザー作成
python manage.py createsuperuser

# Celeryワーカー起動
celery -A config worker -l info

# Celery Beat起動
celery -A config beat -l info

# 静的ファイル収集
python manage.py collectstatic
```

## テスト
```bash
# テスト実行
pytest

# 特定のテスト実行
pytest tests/test_api.py
```

## システム: Darwin (macOS)
