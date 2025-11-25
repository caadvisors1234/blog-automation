# HPBブログ自動化システム 実装計画書

## 概要
本ドキュメントは、HPBブログ自動化システムの実装計画をチェックボックス形式で管理します。
各フェーズを順次実装し、動作確認を行いながら進めます。

**重要**:
- 動作確認は**Docker環境**または**venv仮想環境**上で実行すること
- 本番環境への影響を避けるため、必ず隔離された環境で開発すること

---

## Phase 1: 環境構築（推定: 2-3日）

### 1.1 プロジェクト初期化
- [ ] プロジェクトルートディレクトリ作成
- [ ] Gitリポジトリ初期化
- [ ] `.gitignore` 作成
- [ ] `.env.example` 作成
- [ ] `README.md` 作成

### 1.2 Python環境構築
- [ ] Python 3.12インストール確認
- [ ] venv仮想環境作成: `python -m venv venv`
- [ ] 仮想環境アクティベート: `source venv/bin/activate` (macOS/Linux)
- [ ] `requirements.txt` 作成
- [ ] 依存パッケージインストール: `pip install -r requirements.txt`

### 1.3 Django初期化
- [ ] Django プロジェクト作成: `django-admin startproject config .`
- [ ] アプリケーション作成:
  - [ ] `python manage.py startapp accounts`
  - [ ] `python manage.py startapp blog`
  - [ ] `python manage.py startapp core`
- [ ] アプリをINSTALLED_APPSに追加
- [ ] `settings.py` 基本設定

### 1.4 Docker環境構築
- [ ] `Dockerfile` 作成
- [ ] `docker-compose.yml` 作成
- [ ] `.dockerignore` 作成
- [ ] Dockerイメージビルド: `docker-compose build`
- [ ] コンテナ起動確認: `docker-compose up`

### 1.5 データベース構築
- [ ] PostgreSQL コンテナ起動確認
- [ ] データベース接続設定 (`settings.py`)
- [ ] 初回マイグレーション: `python manage.py migrate`
- [ ] スーパーユーザー作成: `python manage.py createsuperuser`

### 1.6 Redis構築
- [ ] Redis コンテナ起動確認
- [ ] Redis接続確認: `redis-cli ping`
- [ ] Django設定でRedis接続確認

---

## Phase 2: バックエンド実装（推定: 5-7日）

### 2.1 ユーザー管理（accounts アプリ）

#### モデル
- [ ] `User` モデル実装（AbstractUser継承）
- [ ] フィールド追加:
  - [ ] `supabase_uid`
  - [ ] `hpb_salon_url`
  - [ ] `hpb_salon_id`
  - [ ] `salonboard_user_id`（暗号化）
  - [ ] `salonboard_password`（暗号化）
- [ ] マイグレーション作成・適用

#### 暗号化ユーティリティ
- [ ] `apps/accounts/utils.py` 作成
- [ ] `encrypt_credential()` 実装
- [ ] `decrypt_credential()` 実装
- [ ] Fernet暗号化鍵生成・環境変数設定

#### Supabase認証統合
- [ ] Supabaseプロジェクト作成
- [ ] 環境変数設定（SUPABASE_URL, SUPABASE_KEY）
- [ ] `apps/accounts/backends.py` 作成
- [ ] `SupabaseAuthBackend` 実装
- [ ] JWT検証ロジック実装
- [ ] settings.py に認証バックエンド追加

#### ビュー・URL
- [ ] `signup_view` 実装
- [ ] `login_view` 実装
- [ ] `logout_view` 実装
- [ ] `settings_view` 実装（HPB設定・SALON BOARD認証情報）
- [ ] `apps/accounts/urls.py` 作成
- [ ] ルートURLconfに追加

#### 動作確認（venv/Docker）
- [ ] サインアップ動作確認
- [ ] ログイン動作確認
- [ ] ユーザー設定保存確認
- [ ] 暗号化・復号化確認

### 2.2 ブログ投稿（blog アプリ）

#### モデル
- [ ] `BlogPost` モデル実装
  - [ ] 全フィールド定義
  - [ ] ステータス選択肢（draft/processing/completed/failed）
- [ ] `BlogImage` モデル実装
  - [ ] `blog_post` 外部キー
  - [ ] `order` フィールド
  - [ ] UNIQUE制約（blog_post, order）
- [ ] `PostLog` モデル実装
  - [ ] JSONフィールド（scraping_data）
- [ ] マイグレーション作成・適用

#### AI生成（Gemini統合）
- [ ] Gemini APIキー取得
- [ ] 環境変数設定（GEMINI_API_KEY）
- [ ] `apps/blog/ai_generator.py` 作成
- [ ] `generate_blog_content()` 実装
- [ ] プロンプトテンプレート作成
- [ ] レスポンス解析（タイトル・本文抽出）
- [ ] エラーハンドリング

#### スクレイピング
- [ ] `apps/blog/scraper.py` 作成
- [ ] `scrape_stylists()` 実装（T番号抽出）
- [ ] `scrape_coupons()` 実装（クーポン名取得）
- [ ] User-Agent設定
- [ ] エラーハンドリング

#### 動作確認（venv/Docker）
- [ ] Gemini API呼び出し確認
- [ ] 記事生成テスト（キーワード・トーン指定）
- [ ] スクレイピングテスト（実際のHPB URL）

### 2.3 Celery + Redis 統合

#### Celery設定
- [ ] `config/celery.py` 作成
- [ ] `config/__init__.py` 修正（celery_app インポート）
- [ ] settings.py でCelery設定
  - [ ] CELERY_BROKER_URL
  - [ ] CELERY_RESULT_BACKEND
  - [ ] タイムアウト設定

#### タスク実装
- [ ] `apps/blog/tasks.py` 作成
- [ ] `auto_post_blog_task` 実装（骨格のみ）
- [ ] Playwrightインポート（タスク内）

#### Worker起動
- [ ] Celery Worker起動: `celery -A config worker -l info`
- [ ] Celery Beat起動: `celery -A config beat -l info`
- [ ] Flower起動: `celery -A config flower`

#### 動作確認（venv/Docker）
- [ ] ダミータスク実行確認
- [ ] タスクステータス取得確認
- [ ] Flower UIアクセス確認（localhost:5555）

### 2.4 Playwright自動化

#### セレクタ定義
- [ ] `apps/blog/selectors.py` 作成
- [ ] YAML形式でセレクタ定義（または定数クラス）

#### 例外クラス
- [ ] `apps/blog/exceptions.py` 作成
- [ ] `LoginError`
- [ ] `RobotDetectionError`
- [ ] `SalonSelectionError`
- [ ] `ElementNotFoundError`
- [ ] `UploadError`

#### 自動化クラス
- [ ] `apps/blog/automation.py` 作成
- [ ] `SalonBoardAutomation` クラス実装
  - [ ] `__init__()` - ブラウザ初期化
  - [ ] `_login()` - ログイン処理
  - [ ] `_remove_blockers()` - 妨害要素削除
  - [ ] `_check_robot_detection()` - CAPTCHA検知
  - [ ] `_is_multi_salon_page()` - 複数店舗判定
  - [ ] `_select_salon()` - 店舗選択
  - [ ] `_navigate_to_blog_form()` - フォーム遷移
  - [ ] `_fill_blog_form()` - フォーム入力
  - [ ] `_select_coupon()` - クーポン選択
  - [ ] `_insert_content_with_images()` - 本文・画像挿入
  - [ ] `_upload_image()` - 画像アップロード
  - [ ] `_move_cursor_to_end()` - カーソル制御
  - [ ] `post_blog()` - メイン処理

#### Celeryタスク統合
- [ ] `auto_post_blog_task` を完全実装
- [ ] スクレイピング → 自動投稿の流れ実装

#### 動作確認（venv/Docker）
- [ ] Playwrightブラウザ起動確認
- [ ] ログインテスト（実際のSALON BOARD）
- [ ] 妨害要素削除確認
- [ ] 店舗選択確認
- [ ] **注意**: 実際の投稿は慎重に！テスト環境推奨

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

**開始日**: ___________
**完了予定日**: ___________
**実際の完了日**: ___________

**現在のフェーズ**: Phase ___

**課題・ブロッカー**:
-
-

**次のマイルストーン**:
-

---

**作成日**: 2025年1月
**最終更新**: 2025年1月
**ステータス**: 初版作成完了
