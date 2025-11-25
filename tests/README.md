# テストスクリプト

このディレクトリには、HPBブログ自動化システムの動作確認用テストスクリプトが含まれています。

## テストファイル一覧

### 1. test_api.py
**目的**: REST API動作確認
**内容**:
- ユーザー作成テスト
- ブログ記事作成テスト（手動・AI）
- SALONBoardアカウント作成テスト
- データベース操作確認

**実行方法**:
```bash
docker-compose exec web python tests/test_api.py
```

**期待結果**:
- 2件のブログ記事作成
- 1件のSALONBoardアカウント作成
- 全テスト項目PASSED

---

### 2. test_gemini.py
**目的**: Gemini AI統合テスト
**内容**:
- Gemini API接続確認
- ブログ記事生成テスト
- JSON形式レスポンス検証

**実行方法**:
```bash
docker-compose exec web python tests/test_gemini.py
```

**期待結果**:
- API接続成功
- タイトル・本文生成成功
- 処理時間: 約5-15秒

---

### 3. test_celery_task.py
**目的**: Celery非同期タスクテスト
**内容**:
- AI記事生成タスク実行
- タスクステータス追跡
- ステータス自動更新確認

**実行方法**:
```bash
docker-compose exec web python tests/test_celery_task.py
```

**期待結果**:
- タスクステータス: PENDING → STARTED → SUCCESS
- 記事ステータス: draft → generating → ready
- 処理時間: 約14秒

---

### 4. test_hpb_scraper.py
**目的**: HPBスクレイピングテスト
**内容**:
- HPBサロンページスクレイピング
- サロン情報取得確認
- 画像URL取得確認

**実行方法**:
```bash
docker-compose exec web python tests/test_hpb_scraper.py
```

**注意事項**:
- セレクターが古い可能性あり
- 実際のHTML構造に合わせて要更新

**期待結果**:
- HTTP接続成功
- 基本スクレイピング処理完了

---

### 5. test_playwright.py
**目的**: Playwright動作確認
**内容**:
- Chromiumブラウザ起動
- ページナビゲーション
- スクリーンショット取得

**実行方法**:
```bash
docker-compose exec web python tests/test_playwright.py
```

**期待結果**:
- ブラウザ起動成功
- Googleページロード成功
- スクリーンショット生成: `/tmp/playwright_test.png`

---

## 全テスト一括実行

```bash
# API テスト
docker-compose exec web python tests/test_api.py

# Gemini テスト
docker-compose exec web python tests/test_gemini.py

# Celeryタスクテスト
docker-compose exec web python tests/test_celery_task.py

# HPBスクレイパーテスト
docker-compose exec web python tests/test_hpb_scraper.py

# Playwrightテスト
docker-compose exec web python tests/test_playwright.py
```

## テスト結果サマリー（2025-11-25時点）

| テスト | 結果 | 備考 |
|--------|------|------|
| API動作確認 | ✅ PASSED | 全機能正常動作 |
| Gemini統合 | ✅ PASSED | 記事生成成功（14秒） |
| Celeryタスク | ✅ PASSED | 非同期処理正常 |
| HPBスクレイパー | ⚠️ 要更新 | セレクター要確認 |
| Playwright | ✅ PASSED | ブラウザ自動化OK |

## 注意事項

1. **環境要件**
   - Dockerコンテナが起動していること
   - PostgreSQL、Redisが稼働していること
   - Celery WorkerとBeatが起動していること

2. **API キー**
   - `.env`ファイルにGEMINI_API_KEYが設定されていること
   - SUPABASE_URLとSUPABASE_KEYが設定されていること

3. **SALON BOARD投稿**
   - 実際の投稿テストは慎重に実施すること
   - テスト環境での確認推奨

## トラブルシューティング

### テストが失敗する場合

1. **Dockerコンテナ確認**
   ```bash
   docker-compose ps
   ```

2. **ログ確認**
   ```bash
   docker-compose logs web
   docker-compose logs celery_worker
   ```

3. **環境変数確認**
   ```bash
   docker-compose exec web python -c "from django.conf import settings; print(settings.GEMINI_API_KEY[:20])"
   ```

4. **データベース接続確認**
   ```bash
   docker-compose exec web python manage.py dbshell
   ```

5. **Redis接続確認**
   ```bash
   docker-compose exec redis redis-cli ping
   ```

---

**最終更新**: 2025-11-25
**テスト実施者**: Claude Code AI Assistant
