# blog-automation アーキテクチャ詳細

## クラス構成

### apps/accounts/
- **User** (10-78行): カスタムユーザーモデル
  - フィールド: supabase_user_id, hpb_salon_url, hpb_salon_id
  - メソッド: save(), _extract_salon_id()（URLからサロンIDを自動抽出）

### apps/blog/models.py
- **BlogPost** (10-148行): ブログ投稿モデル
  - STATUS_CHOICES: draft, generating, ready, publishing, published, failed
  - フィールド: user, title, content, generated_content, status, ai_prompt, tone, keywords, ai_generated, stylist_id, coupon_name, celery_task_id, salon_board_url, published_at
  - メソッド: clean(), get_image_count(), is_processable()

- **BlogImage** (151-200行): 画像モデル
  - フィールド: blog_post, image_file, order（最大4枚）
  - プロパティ: image_url, file_path

- **PostLog** (203-289行): 投稿ログ
  - STATUS_CHOICES: pending, in_progress, success, failed
  - フィールド: user, blog_post, status, error_message, screenshot_path, scraping_data, duration_seconds, started_at, completed_at

- **SALONBoardAccount** (292-356行): SALON BOARD認証情報
  - フィールド: user (OneToOne), login_id, encrypted_password（暗号化）, is_active
  - メソッド: get_credentials(), set_password()（Fernetで暗号化）

### apps/blog/views.py
- **BlogPostViewSet**: 
  - アクション: generate（AI生成開始）, publish（SALON BOARD投稿）, images（画像取得）, stats（ダッシュボード統計）
- **テンプレートビュー**: `post_create` はキーワード必須（空の場合はエラーを返し、タイトル/AI指示欄は存在しない）
- **BlogImageViewSet**: 画像CRUD
- **PostLogViewSet**: 投稿ログ読み取り専用

### apps/blog/serializers.py (2025-11-25 修正)
- **BlogPostCreateSerializer.create()**: 
  - userはViewSet.perform_create()からvalidated_dataに渡される
  - create()内で直接userを取得しない（二重設定バグ防止済み）
  - `validate_keywords()` で空入力を弾き、トリムした文字列を保存

### apps/blog/tasks.py
- **generate_blog_content_task**: 
  - キーワード必須（欠落時は即 failed）
  - ユーザー提供の `ai_prompt` があれば優先使用し、なければキーワード/トーンから定型プロンプトを自動生成
  - 画像枚数に応じて `{{image_n}}` プレースホルダーの挿入指示を付与
- **generate_blog_content_task**: AI生成Celeryタスク（max_retries=3, リトライ間隔60秒×）
- **publish_to_salon_board_task**: SALON BOARD投稿タスク（max_retries=3, リトライ間隔120秒×）
- **cleanup_old_failed_posts**: 古い失敗投稿クリーンアップ
- **cleanup_old_logs**: 古いログクリーンアップ

### apps/blog/gemini_client.py
- **GeminiClient**: Google Gemini AIクライアント
  - generate_blog_content(): プロンプトからブログコンテンツ生成
  - enhance_title(): タイトル改善

### apps/blog/salon_board_client.py
- **SALONBoardClient**: Playwright使用のSALON BOARD自動投稿
  - コンテキストマネージャ対応（with文使用可）
  - メソッド: start(), close(), login(), select_salon(), select_stylist(), select_coupon(), publish_blog_post()
  - プライベート: _prepare_content_with_images(), _upload_images()

### apps/blog/hpb_scraper.py  
- **HPBScraper**: BeautifulSoup4使用のHPBスクレイパー
  - scrape_stylists(): スタイリスト情報取得（ページネーション対応）
  - scrape_coupons(): クーポン情報取得
  - _is_valid_coupon_name(): クーポン名バリデーション
- 関数: scrape_stylists(), scrape_coupons()（クラスのラッパー）

## データフロー
1. ユーザーがBlogPost作成（draft状態）
2. generate アクション → status='generating' → Celeryタスク起動 → GeminiClient.generate_blog_content() → status='ready'
3. publish アクション → status='publishing' → Celeryタスク起動 → SALONBoardClient.publish_blog_post() → status='published'
4. 各ステップでPostLogに記録
