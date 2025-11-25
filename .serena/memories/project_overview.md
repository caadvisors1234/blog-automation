# blog-automation プロジェクト概要

## 目的
HPB（Hot Pepper Beauty）ブログ自動化システム。AIによるブログ記事生成とSALON BOARDへの自動投稿を行う。

## 技術スタック
- **Backend**: Python 3.12 / Django 5.0.0 / Django REST Framework 3.14.0
- **Database**: PostgreSQL 16
- **Async Task**: Celery + Redis
- **Auth**: Supabase Auth
- **Browser Automation**: Playwright
- **AI**: Google Gemini 2.5 Flash (google-genai 0.2.2)
- **Scraping**: BeautifulSoup4

## 主なアプリ構成
- `apps/accounts/`: ユーザー認証管理
- `apps/blog/`: ブログ投稿機能、AI生成、自動投稿
- `apps/core/`: 共通機能

## 主要モデル
- `User`: カスタムユーザーモデル（supabase_user_id, hpb_salon_url, hpb_salon_id）
- `BlogPost`: ブログ投稿（status, title, content, stylist_id, coupon_name, celery_task_id等）
- `BlogImage`: ブログ画像（最大4枚）
- `PostLog`: 投稿実行ログ
- `SALONBoardAccount`: SALON BOARD認証情報（login_id, 暗号化パスワード）

## API構成
- ViewSetベースのREST API
- `/api/blog/posts/`: BlogPost CRUD + generate/publishアクション + imagesアクション
- `/api/blog/images/`: BlogImage CRUD
- `/api/blog/logs/`: PostLog 読み取り専用
- `/api/accounts/users/me/`: ユーザー情報
- `/api/accounts/salon-board-accounts/`: SALON BOARDアカウント管理

## 更新履歴
- 2025年11月: モデル更新（BlogImage, PostLog追加）、ドキュメント整合性確保
- 2025年11月25日: WebSocket実装完了（Phase 2.5）
  - consumers.py: BlogProgressConsumer, TaskStatusConsumer
  - routing.py: ws/blog/progress/, ws/task/
  - progress.py: ProgressNotifier, send_progress(), send_error()
  - tasks.py: リアルタイム進捗通知統合
- 2025年11月25日: フロントエンド実装完了（Phase 2.6 + Phase 3）
  - テンプレート: base.html, dashboard.html, blog/*, accounts/*, errors/*
  - 静的ファイル: custom.css, websocket.js, main.js
  - ビュー: dashboard, login/logout, settings, post CRUD
  - URLルーティング: core, accounts, blog 全て設定済み
- 2025年11月25日: AI生成機能改善
  - 3案同時生成: GeminiClient.generate_blog_content_variations()
  - 選択フロー: generating.html → select_article.html → detail.html
  - JSONパース安定化: _extract_json_from_text()メソッド
  - 新ステータス: 'selecting'（記事選択待ち状態）
  - 新フィールド: BlogPost.generated_variations（JSONField）