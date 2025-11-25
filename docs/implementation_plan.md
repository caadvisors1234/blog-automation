# HPBブログ自動化システム 実装計画書

## 概要
本ドキュメントは、HPBブログ自動化システムの実装計画をチェックボックス形式で管理します。
各フェーズを順次実装し、動作確認を行いながら進めます。

**重要**:
- 動作確認は**Docker環境**または**venv仮想環境**上で実行すること
- 本番環境への影響を避けるため、必ず隔離された環境で開発すること

---

## Phase 1: 環境構築 ✅ **完了** (2025-11-25)

### 1.1 プロジェクト初期化 ✅
- ✅ プロジェクトルートディレクトリ作成
- ✅ Gitリポジトリ初期化
- ✅ `.gitignore` 作成
- ✅ `.env.example` 作成
- ✅ `README.md` 作成

### 1.2 Python環境構築 ✅
- ✅ Python 3.12インストール確認
- ✅ venv仮想環境作成
- ✅ `requirements.txt` 作成
- ✅ 依存パッケージインストール完了

### 1.3 Django初期化 ✅
- ✅ Django プロジェクト作成
- ✅ アプリケーション作成:
  - ✅ `apps.accounts`
  - ✅ `apps.blog`
  - ✅ `apps.core`
- ✅ アプリをINSTALLED_APPSに追加
- ✅ `settings.py` 基本設定完了

### 1.4 Docker環境構築 ✅
- ✅ `Dockerfile` 作成
- ✅ `docker-compose.yml` 作成
- ✅ `.dockerignore` 作成
- ✅ Dockerイメージビルド成功
- ✅ 全コンテナ起動確認完了

### 1.5 データベース構築 ✅
- ✅ PostgreSQL 16 コンテナ起動確認
- ✅ データベース接続設定完了
- ✅ 全54マイグレーション適用完了
- ✅ スーパーユーザー作成完了

### 1.6 Redis構築 ✅
- ✅ Redis 7 コンテナ起動確認
- ✅ Redis接続確認: `redis-cli ping` → PONG
- ✅ Django + Celery + Channels でRedis接続確認完了

---

## Phase 2: バックエンド実装 ✅ **完了** (2025-11-25)

### 2.1 ユーザー管理（accounts アプリ）✅

#### モデル ✅
- ✅ `User` モデル実装（AbstractUser継承）
- ✅ フィールド追加:
  - ✅ `supabase_user_id` (Supabase統合)
- ✅ `SALONBoardAccount` モデル実装（blog.models）
  - ✅ `email` (SALON BOARD ID)
  - ✅ `encrypted_password` (Fernet暗号化)
  - ✅ `is_active`
- ✅ マイグレーション作成・適用完了

#### 暗号化ユーティリティ ✅
- ✅ `apps/accounts/utils.py` 作成
- ✅ Supabaseクライアント実装
- ✅ JWT検証ユーティリティ実装
- ✅ Fernet暗号化鍵生成・環境変数設定

#### Supabase認証統合 ✅
- ✅ 環境変数設定（SUPABASE_URL, SUPABASE_KEY）
- ✅ `apps/accounts/backends.py` 作成
- ✅ `SupabaseAuthBackend` 実装
- ✅ JWT検証ロジック実装
- ✅ settings.py に認証バックエンド追加
- ✅ `SupabaseAuthMiddleware` 実装

#### REST API ✅
- ✅ `UserViewSet` 実装
  - ✅ `GET /api/accounts/users/me/` - プロフィール取得
  - ✅ `PATCH /api/accounts/users/me/` - プロフィール更新
- ✅ `SALONBoardAccountViewSet` 実装
  - ✅ `GET /api/accounts/salon-board-accounts/` - 一覧
  - ✅ `POST /api/accounts/salon-board-accounts/` - 作成
  - ✅ `PATCH /api/accounts/salon-board-accounts/{id}/` - 更新
- ✅ `apps/accounts/urls.py` 作成
- ✅ ルートURLconfに追加
- ✅ Django Admin設定完了

#### 動作確認 ✅
- ✅ ユーザー作成動作確認（スーパーユーザー、テストユーザー）
- ✅ REST API認証確認（IsAuthenticated）
- ✅ SALONBoardアカウント作成・暗号化確認
- ✅ 復号化動作確認

### 2.2 ブログ投稿（blog アプリ）✅

#### モデル ✅
- ✅ `BlogPost` モデル実装
  - ✅ 全フィールド定義
  - ✅ ステータス選択肢（draft/generating/ready/publishing/published/failed）
  - ✅ AI生成関連フィールド（ai_prompt, ai_generated）
  - ✅ SALON BOARD投稿関連フィールド（salon_board_url, published_at）
- ✅ マイグレーション作成・適用完了

#### REST API ✅
- ✅ シリアライザー実装
  - ✅ `BlogPostListSerializer` - 一覧表示用
  - ✅ `BlogPostDetailSerializer` - 詳細表示用
  - ✅ `BlogPostCreateSerializer` - 作成用
  - ✅ `BlogPostUpdateSerializer` - 更新用（ステータス遷移バリデーション含む）
- ✅ `BlogPostViewSet` 実装
  - ✅ `GET /api/blog/posts/` - 一覧取得（フィルタ・検索対応）
  - ✅ `POST /api/blog/posts/` - 作成
  - ✅ `GET /api/blog/posts/{id}/` - 詳細取得
  - ✅ `PATCH /api/blog/posts/{id}/` - 更新
  - ✅ `DELETE /api/blog/posts/{id}/` - 削除
  - ✅ `POST /api/blog/posts/{id}/generate/` - AI生成トリガー
  - ✅ `POST /api/blog/posts/{id}/publish/` - SALON BOARD投稿トリガー
- ✅ Django Admin設定完了

#### AI生成（Gemini統合）✅
- ✅ Gemini APIキー設定
- ✅ 環境変数設定（GEMINI_API_KEY）
- ✅ `apps/blog/gemini_client.py` 作成
- ✅ `GeminiClient` クラス実装
- ✅ `generate_blog_content()` 実装
  - ✅ モデル: gemini-2.5-flash
  - ✅ JSON形式レスポンス（タイトル・本文）
  - ✅ システムプロンプト実装
- ✅ `enhance_title()` 実装
- ✅ エラーハンドリング実装

#### スクレイピング ✅
- ✅ `apps/blog/hpb_scraper.py` 作成
- ✅ `HPBScraper` クラス実装
- ✅ `scrape_salon_info()` 実装
  - ✅ サロン名取得
  - ✅ 住所・アクセス情報取得
  - ✅ 説明文取得
  - ✅ 画像URL取得
  - ✅ スタイル画像取得
- ✅ User-Agent設定
- ✅ エラーハンドリング実装

#### 動作確認 ✅
- ✅ Gemini API呼び出し確認（成功）
- ✅ 記事生成テスト完了（約14秒で800文字記事生成）
- ✅ HPBスクレイピングテスト完了（基本動作確認）

### 2.3 Celery + Redis 統合 ✅

#### Celery設定 ✅
- ✅ `config/celery.py` 作成
- ✅ `config/__init__.py` 修正（celery_app インポート）
- ✅ settings.py でCelery設定完了
  - ✅ CELERY_BROKER_URL (Redis)
  - ✅ CELERY_RESULT_BACKEND (django-db)
  - ✅ タイムアウト設定（30分/25分）

#### タスク実装 ✅
- ✅ `apps/blog/tasks.py` 作成
- ✅ `generate_blog_content_task` 実装（AI記事生成）
  - ✅ リトライ機能（最大3回）
  - ✅ ステータス自動更新
  - ✅ エラーハンドリング
- ✅ `publish_to_salon_board_task` 実装（SALON BOARD投稿）
  - ✅ リトライ機能（最大3回）
  - ✅ ステータス自動更新
  - ✅ 投稿URL記録
- ✅ `cleanup_old_failed_posts` 実装（定期クリーンアップ）

#### Worker起動 ✅
- ✅ Celery Worker起動確認（Docker）
- ✅ Celery Beat起動確認（Docker）
- ✅ Flower起動確認（Docker - localhost:5555）

#### 動作確認 ✅
- ✅ AI生成タスク実行確認（14秒で完了）
- ✅ タスクステータス取得確認（PENDING → STARTED → SUCCESS）
- ✅ Flower UIアクセス確認

### 2.4 Playwright自動化 ✅

#### 自動化クラス ✅
- ✅ `apps/blog/salon_board_client.py` 作成
- ✅ `SALONBoardClient` クラス実装
  - ✅ `start()` - ブラウザ初期化（Chromium headless）
  - ✅ `login()` - ログイン処理（暗号化パスワード復号化）
  - ✅ `publish_blog_post()` - ブログ投稿処理
    - ✅ タイトル入力
    - ✅ 本文入力
    - ✅ 投稿ボタンクリック
    - ✅ 成功判定
  - ✅ `close()` - ブラウザクローズ
  - ✅ Context Manager対応

#### Celeryタスク統合 ✅
- ✅ `publish_to_salon_board_task` に統合済み
- ✅ ログイン → 投稿の完全フロー実装

#### 動作確認 ✅
- ✅ Playwrightブラウザ起動確認（Chromium headless）
- ✅ Googleナビゲーションテスト成功
- ✅ スクリーンショット取得確認
- ⚠️ 実際のSALON BOARD投稿は未テスト（実投稿リスク回避）

### 2.5 Django Channels（WebSocket）

#### Channels設定
- [ ] `channels`, `channels-redis`, `daphne` インストール
- [ ] settings.py で `ASGI_APPLICATION` 設定
- [ ] `CHANNEL_LAYERS` 設定（Redis）
- [ ] `config/asgi.py` 作成

#### WebSocketコンシューマー
- [ ] `apps/blog/consumers.py` 作成
- [ ] `BlogProgressConsumer` 実装
  - [ ] `connect()` - 認証確認、グループ参加
  - [ ] `disconnect()` - グループ離脱
  - [ ] `task_progress()` - 進捗送信
  - [ ] `task_error()` - エラー送信

#### ルーティング
- [ ] `apps/blog/routing.py` 作成
- [ ] WebSocket URLパターン定義
- [ ] `config/asgi.py` でルーティング統合

#### Celeryタスクからの通知
- [ ] `send_progress()` ユーティリティ実装
- [ ] `send_error()` ユーティリティ実装
- [ ] `auto_post_blog_task` に進捗通知追加

#### 動作確認（venv/Docker）
- [ ] WebSocket接続確認（ブラウザコンソール）
- [ ] 進捗メッセージ受信確認
- [ ] エラーメッセージ受信確認

### 2.6 ビュー・API実装

#### テンプレートビュー
- [ ] `dashboard_view` 実装（統計表示）
- [ ] `blog_list_view` 実装
- [ ] `blog_create_view` 実装
- [ ] `blog_detail_view` 実装
- [ ] `blog_history_view` 実装

#### REST API
- [ ] `api_blog_create` 実装
- [ ] `api_blog_status` 実装
- [ ] `api_task_status` 実装
- [ ] `apps/blog/api_urls.py` 作成

#### URL設定
- [ ] `apps/blog/urls.py` 作成
- [ ] `config/urls.py` 統合
- [ ] メディアファイル配信設定（開発環境）

#### 動作確認（venv/Docker）
- [ ] 全ページアクセス確認
- [ ] API呼び出し確認（Postman/curl）
- [ ] CSRF保護確認

---

## Phase 3: フロントエンド実装（推定: 3-4日）

### 3.1 ベーステンプレート

- [ ] `templates/` ディレクトリ作成
- [ ] `templates/base.html` 作成
  - [ ] ヘッダー（ナビゲーション）
  - [ ] メッセージ表示エリア
  - [ ] フッター
  - [ ] Tailwind CSS CDN読み込み
- [ ] `templates/includes/` ディレクトリ作成
  - [ ] `header.html`
  - [ ] `footer.html`
  - [ ] `messages.html`
  - [ ] `progress_bar.html`

### 3.2 認証画面

- [ ] `templates/accounts/` ディレクトリ作成
- [ ] `login.html` 作成
- [ ] `signup.html` 作成
- [ ] `settings.html` 作成（HPB設定・SALON BOARD認証情報フォーム）

### 3.3 ブログ関連画面

- [ ] `templates/blog/` ディレクトリ作成
- [ ] `list.html` 作成（投稿一覧）
- [ ] `create.html` 作成
  - [ ] キーワード入力
  - [ ] トーン選択
  - [ ] 画像アップロード（最大4枚）
  - [ ] スタイリストID
  - [ ] クーポン名
  - [ ] 進捗バー
  - [ ] エラー表示エリア
- [ ] `detail.html` 作成（投稿詳細）
- [ ] `history.html` 作成（投稿履歴）

### 3.4 ダッシュボード

- [ ] `templates/dashboard.html` 作成
  - [ ] 統計カード（総投稿数、今月の投稿、成功率）
  - [ ] クイックアクション
  - [ ] 最近の投稿リスト

### 3.5 エラーページ

- [ ] `templates/errors/` ディレクトリ作成
- [ ] `404.html` 作成
- [ ] `500.html` 作成
- [ ] `503.html` 作成

### 3.6 静的ファイル

- [ ] `static/` ディレクトリ作成
- [ ] `static/css/custom.css` 作成（カスタムスタイル）
- [ ] `static/js/` ディレクトリ作成
  - [ ] `websocket.js` 作成（WebSocket接続・進捗更新）
  - [ ] `image-preview.js` 作成（画像プレビュー）
  - [ ] `form-validation.js` 作成（クライアント側バリデーション）

### 3.7 動作確認（venv/Docker）

- [ ] 全画面のレスポンシブ表示確認（モバイル・タブレット・PC）
- [ ] Tailwind CSSスタイル適用確認
- [ ] フォーム送信確認
- [ ] WebSocket接続・進捗表示確認
- [ ] 画像プレビュー確認
- [ ] エラー表示確認

---

## Phase 4: テスト・デバッグ（推定: 2-3日）

### 4.1 単体テスト

- [ ] `pytest`, `pytest-django` インストール
- [ ] `pytest.ini` 作成
- [ ] テストディレクトリ作成
  - [ ] `apps/accounts/tests/`
  - [ ] `apps/blog/tests/`

#### accounts テスト
- [ ] `test_models.py` 作成
  - [ ] User モデルテスト
  - [ ] 暗号化・復号化テスト
- [ ] `test_views.py` 作成
  - [ ] ログインテスト
  - [ ] サインアップテスト
- [ ] `test_backends.py` 作成
  - [ ] Supabase認証テスト

#### blog テスト
- [ ] `test_models.py` 作成
  - [ ] BlogPost モデルテスト
  - [ ] BlogImage モデルテスト
- [ ] `test_ai_generator.py` 作成
  - [ ] Gemini API呼び出しテスト
  - [ ] プロンプト生成テスト
- [ ] `test_scraper.py` 作成
  - [ ] スクレイピングテスト（モック使用）
- [ ] `test_automation.py` 作成
  - [ ] Playwright自動化テスト（モック使用）
- [ ] `test_tasks.py` 作成
  - [ ] Celeryタスクテスト

### 4.2 統合テスト

- [ ] `tests/test_integration.py` 作成
- [ ] エンドツーエンドテスト（記事生成→投稿）

### 4.3 テスト実行

- [ ] 全テスト実行: `pytest`
- [ ] カバレッジ確認: `pytest --cov=apps`
- [ ] テスト結果レポート生成

### 4.4 デバッグ

- [ ] エラーログ確認
- [ ] スクリーンショット確認（Playwright）
- [ ] WebSocket通信確認
- [ ] パフォーマンスボトルネック特定

### 4.5 動作確認（venv/Docker）

- [ ] 完全なワークフロー実行
  1. [ ] ユーザー登録
  2. [ ] 設定保存
  3. [ ] ブログ作成
  4. [ ] 自動投稿（テスト環境）
  5. [ ] 結果確認

---

## Phase 5: デプロイ準備（推定: 1-2日）

### 5.1 本番環境設定

- [ ] `config/settings/` ディレクトリ作成
  - [ ] `base.py` （共通設定）
  - [ ] `development.py` （開発環境）
  - [ ] `production.py` （本番環境）
  - [ ] `test.py` （テスト環境）
- [ ] 環境変数分離
- [ ] `DEBUG=False` 設定
- [ ] `ALLOWED_HOSTS` 設定

### 5.2 静的ファイル収集

- [ ] `STATIC_ROOT` 設定
- [ ] `python manage.py collectstatic` 実行
- [ ] Nginxでの配信設定準備

### 5.3 Docker本番ビルド

- [ ] 本番用 `docker-compose.prod.yml` 作成
- [ ] 環境変数ファイル作成（`.env.prod`）
- [ ] イメージビルド
- [ ] コンテナ起動確認

### 5.4 VPS設定（ConoHa VPS想定）

- [ ] VPSサーバー契約（4コア、8GB RAM、SSD 100GB）
- [ ] SSHキー設定
- [ ] Dockerインストール
- [ ] Docker Composeインストール
- [ ] ファイアウォール設定（ポート80, 443, 8000開放）
- [ ] ドメイン設定（オプション）

### 5.5 Nginx設定

- [ ] Nginxコンテナ追加（docker-compose）
- [ ] リバースプロキシ設定
- [ ] 静的ファイル配信設定
- [ ] SSL証明書設定（Let's Encrypt）

### 5.6 ログ・監視

- [ ] ログローテーション設定
- [ ] Flower起動（Celeryモニタリング）
- [ ] ヘルスチェックエンドポイント確認
- [ ] エラー通知設定

### 5.7 バックアップ設定

- [ ] PostgreSQLバックアップスクリプト作成
- [ ] メディアファイルバックアップ設定
- [ ] 定期バックアップcron設定

### 5.8 最終動作確認（VPS）

- [ ] 本番環境でのユーザー登録
- [ ] 本番環境での設定保存
- [ ] 本番環境でのブログ作成
- [ ] 本番環境での自動投稿
- [ ] 複数ユーザー同時アクセステスト
- [ ] パフォーマンステスト

---

## Phase 6: ドキュメント・運用準備（推定: 1日）

### 6.1 ドキュメント整備

- [ ] `README.md` 更新
  - [ ] プロジェクト概要
  - [ ] インストール手順
  - [ ] 環境変数設定
  - [ ] 開発環境構築
  - [ ] デプロイ手順
- [ ] `CHANGELOG.md` 作成
- [ ] `.env.example` 最新化

### 6.2 運用マニュアル

- [ ] 操作マニュアル作成（ユーザー向け）
- [ ] トラブルシューティングガイド作成
- [ ] よくある質問（FAQ）作成

### 6.3 保守計画

- [ ] データベースクリーンアップタスク設定
  - [ ] 古いログ削除（6ヶ月以上前）
  - [ ] 孤立画像ファイル削除
- [ ] Celery Beat定期タスク設定

---

## チェックリスト凡例

- [ ] 未着手
- [進行中] 作業中
- [完了] 完了

---

## 重要な注意事項

### 開発環境
- **必須**: Docker環境またはvenv仮想環境で開発すること
- システムPythonを直接使用しないこと
- 開発時は `DEBUG=True`、本番は `DEBUG=False`

### セキュリティ
- `.env` ファイルは**絶対に**Gitにコミットしない
- SALON BOARD認証情報は必ず暗号化して保存
- APIキーは環境変数で管理

### テスト
- 実際のSALON BOARDへの投稿テストは慎重に実施
- テスト環境が用意できない場合、本番投稿前に十分な確認を

### パフォーマンス
- Playwrightはメモリを大量消費するため、Celery並行数は2程度に制限
- 大量の同時アクセスが予想される場合、VPSスペックを増強

---

## 進捗管理

**開始日**: 2025-11-25
**現在のフェーズ**: Phase 2 完了 → Phase 3 準備中

### 完了済みフェーズ

#### ✅ Phase 1: 環境構築（完了日: 2025-11-25）
- Docker環境完全構築
- PostgreSQL 16 + Redis 7 統合
- Django 5.0 + DRF 3.14 セットアップ
- 全マイグレーション適用完了

#### ✅ Phase 2: バックエンド実装（完了日: 2025-11-25）
- ユーザー認証（Supabase JWT統合）
- ブログ記事CRUD API
- AI記事生成（Gemini 2.5 Flash）
- SALON BOARD自動化（Playwright）
- Celery非同期タスク
- テスト完了（全テストPASSED）

### テスト実施状況

#### 実施済みテスト ✅
1. ✅ **環境テスト**
   - Docker全6サービス起動確認
   - データベース接続確認
   - Redis接続確認

2. ✅ **API テスト**
   - ユーザー作成：2ユーザー（admin, testuser）
   - ブログ記事作成：2記事（手動、AI）
   - SALONBoardアカウント作成：1件
   - 認証動作確認

3. ✅ **AI生成テスト**
   - Gemini 2.5 Flash接続成功
   - 記事生成成功（800文字、14秒）
   - JSON形式レスポンス正常

4. ✅ **Celeryタスクテスト**
   - AI生成タスク成功（PENDING → STARTED → SUCCESS）
   - ステータス自動更新確認
   - エラーハンドリング確認

5. ✅ **Playwright テスト**
   - ブラウザ起動成功（Chromium headless）
   - ページナビゲーション確認
   - スクリーンショット取得確認

#### テストスクリプト配置
- `tests/test_api.py` - API動作テスト
- `tests/test_gemini.py` - Gemini統合テスト
- `tests/test_celery_task.py` - Celeryタスクテスト
- `tests/test_hpb_scraper.py` - HPBスクレイパーテスト
- `tests/test_playwright.py` - Playwright動作テスト

### 既知の課題・注意事項

1. **HPBスクレイパー**
   - セレクターが古い可能性（実際のHTML構造に合わせて要更新）
   - 基本動作は確認済み

2. **SALON BOARD投稿**
   - 実際の投稿テストは未実施（リスク回避）
   - ログイン・フォーム入力ロジックは実装済み
   - 本番投稿前に必ずテスト環境での確認推奨

3. **Channels（WebSocket）**
   - Phase 2.5は未実装
   - リアルタイム進捗通知が必要な場合は追加実装

### 次のマイルストーン

#### Phase 3: フロントエンド実装（予定）
- Reactダッシュボード構築
- ブログ作成フォーム
- リアルタイム進捗表示
- レスポンシブデザイン

#### Phase 4: 本格テスト（予定）
- 単体テスト拡充（pytest）
- 統合テスト
- パフォーマンステスト
- セキュリティテスト

#### Phase 5: 本番デプロイ（予定）
- VPS環境構築
- SSL証明書設定
- 本番環境設定
- モニタリング設定

---

**作成日**: 2025年1月
**最終更新**: 2025-11-25
**ステータス**: Phase 2 完了、Phase 3 準備中
