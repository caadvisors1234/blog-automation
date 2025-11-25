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

- **PostLog** (214-300行): 投稿ログ
  - STATUS_CHOICES: in_progress, success, failed
  - フィールド: user, blog_post, status, error_message, screenshot_path, scraping_data, duration_seconds, started_at, completed_at
  - メソッド: calculate_duration() （duration_secondsを自動計算してsave）
  - **重要**: フィールド名は `duration_seconds` であり `duration` ではない

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

### apps/blog/tasks.py (2025-11-25 エラー処理改善)
- **generate_blog_content_task**: AI生成Celeryタスク（max_retries=3, リトライ間隔60秒）
  - キーワード必須（欠落時は即 failed）
  - ユーザー提供の `ai_prompt` があれば優先使用し、なければキーワード/トーンから定型プロンプトを自動生成
  - 画像枚数に応じて `{{image_n}}` プレースホルダーの挿入指示を付与
- **publish_to_salon_board_task**: SALON BOARD投稿タスク（max_retries=3, リトライ間隔120秒）
  - **エラー処理**: データベース保存を通知送信より先に実行（AsyncSync エラー回避）
  - 早期バリデーション: タイトル・本文欠如、アカウント無効時も post_log.save() を実行
  - 例外ハンドラ: RobotDetectionError, LoginError, SalonSelectionError, SALONBoardError, Exception
  - すべてのエラー処理で post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration_seconds']) を呼び出し
- **cleanup_old_failed_posts**: 古い失敗投稿クリーンアップ
- **cleanup_old_logs**: 古いログクリーンアップ

### apps/blog/progress.py (2025-11-25 非同期対応)
- **ProgressNotifier**: Celery タスクから WebSocket クライアントへ進捗通知を送信
  - 初期化: post_id, user_id, task_type, task_id
  - グループ: user_group (`blog_progress_{user_id}`), post_group (`blog_progress_post_{post_id}`)
  - メソッド: 
    - send_started(): タスク開始通知
    - send_progress(progress, message): 進捗更新（0-100%）
    - send_completed(result, message): 完了通知
    - send_failed(error, message): 失敗通知
    - send_status_update(old_status, new_status): ステータス変更通知
  - **非同期対応**: 
    - 同期コンテキスト（Celery）: `async_to_sync()` を使用
    - 非同期コンテキスト（WebSocket）: `asyncio.create_task()` を使用
    - `asyncio.get_running_loop()` でコンテキストを検出し、適切な方法を選択
  - 便利関数: send_progress(), send_error(), send_status_change()

### apps/blog/gemini_client.py
- **GeminiClient**: Google Gemini AIクライアント
  - generate_blog_content(): プロンプトからブログコンテンツ生成
  - enhance_title(): タイトル改善

### apps/blog/salon_board_client.py (2025-11-25 nicEdit実装修正)
- **SALONBoardClient**: Playwright使用のSALON BOARD自動投稿
  - コンテキストマネージャ対応（with文使用可）
  - メソッド: start(), close(), login(), select_salon(), select_stylist(), select_coupon(), publish_blog_post()
  - プライベート: 
    - _fill_content_with_images(): nicEditor API/contenteditable div/textarea の3層フォールバック
    - _set_cursor_at_end_nicedit(): Range API を使用したカーソル制御（div.nicEdit-main に対して操作）
    - _upload_single_image(): 画像アップロード
  - **重要**: nicEdit は iframe を使用せず、contenteditable div を使用
  - セレクタ: 
    - editor_div: "div.nicEdit-main[contenteditable='true']" （カーソル制御対象）
    - editor_textarea: "textarea#blogContents" （nicEditor API バインド先）

### apps/blog/hpb_scraper.py  
- **HPBScraper**: BeautifulSoup4使用のHPBスクレイパー
  - scrape_stylists(): スタイリスト情報取得（ページネーション対応）
  - scrape_coupons(): クーポン情報取得
  - _is_valid_coupon_name(): クーポン名バリデーション
- 関数: scrape_stylists(), scrape_coupons()（クラスのラッパー）

## データフロー（2025-11-25 更新）
1. ユーザーが新規作成画面でキーワード入力 → 「AIで記事を生成」ボタン
2. BlogPost作成（generating状態）→ Celeryタスク即時起動
3. GeminiClient.generate_blog_content_variations() → 3案生成 → status='selecting'
4. ユーザーが3案選択画面で好みの記事を選択
5. 選択した案をtitle/contentに保存 → status='ready'
2. generate アクション → status='generating' → Celeryタスク起動 → GeminiClient.generate_blog_content() → status='ready'
3. publish アクション → status='publishing' → Celeryタスク起動 → SALONBoardClient.publish_blog_post() → status='published'
4. 各ステップでPostLogに記録
