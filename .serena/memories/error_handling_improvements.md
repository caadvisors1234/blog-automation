# エラー処理とテスト改善 (2025-11-25)

## AsyncSync エラー問題と修正

### 問題の背景

Celery タスクから Django Channels の `ProgressNotifier.send_*()` メソッドを呼び出すと、以下のエラーが発生：

```
You cannot call this from an async context - use a thread or sync_to_async.
```

### 根本原因

1. `ProgressNotifier._send_to_groups()` は内部で `async_to_sync()` を使用
2. データベース操作（`post.save()`, `post_log.save()`）の**前**に通知を送信
3. `async_to_sync()` が非同期コンテキストを作成
4. その後の Django ORM 操作（同期）が失敗

### 修正内容

#### 1. データベース操作と通知の順序変更 (`apps/blog/tasks.py`)

すべてのエラーハンドラで以下のパターンを適用：

```python
# 修正前: 通知が先
post_log.status = 'failed'
post_log.error_message = str(e)
post_log.completed_at = timezone.now()
post_log.calculate_duration()
# ❌ post_log.save() が呼ばれていない
notifier.send_failed(...)  # ❌ 先に非同期コンテキスト作成
return {'success': False, ...}

# 修正後: データベース操作が先
# Save to database BEFORE sending notifications
try:
    post.status = 'failed'
    post.save(update_fields=['status'])
    post_log.status = 'failed'
    post_log.error_message = str(e)
    post_log.completed_at = timezone.now()
    post_log.calculate_duration()
    post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration_seconds'])  # ✅
except Exception as db_error:
    logger.error(f"Failed to save to database: {db_error}")

# Send notification after database operations
try:
    notifier.send_failed(...)  # ✅ データベース保存後
except Exception as notif_error:
    logger.error(f"Failed to send notification: {notif_error}")

return {'success': False, ...}
```

**修正箇所**:
- タイトル・本文欠如エラー (line 263-287)
- SALON BOARD アカウント無効エラー (line 291-320)
- RobotDetectionError (line 373-398)
- LoginError (line 400-425)
- SalonSelectionError (line 427-452)
- SALONBoardError (line 454-485)
- General Exception (line 487-518)
- 成功時の処理 (line 331-369)

#### 2. 非同期コンテキスト対応 (`apps/blog/progress.py`)

`ProgressNotifier._send_to_groups()` と `_send_to_task_group()` を修正：

```python
# 修正前: 非同期コンテキストでは通知をスキップ
try:
    asyncio.get_running_loop()
    # ❌ 非同期コンテキストでは即 return
    logger.debug("AsyncToSync called from async context, skipping notification")
    return
except RuntimeError:
    # 同期コンテキスト
    async_to_sync(self.channel_layer.group_send)(...)

# 修正後: 非同期コンテキストでは create_task を使用（エラーハンドリング付き）
try:
    loop = asyncio.get_running_loop()
    # ✅ 非同期コンテキストでは create_task
    async def send_async():
        try:
            await self.channel_layer.group_send(self.user_group, event)
            await self.channel_layer.group_send(self.post_group, event)
            logger.debug("Notification sent successfully via asyncio.create_task")
        except Exception as e:
            # ✅ タスク内の例外を捕捉してログ出力
            logger.error(f"Failed to send notification in async task: {e}")
    
    asyncio.create_task(send_async())
    logger.debug("Scheduled notification via asyncio.create_task")
except RuntimeError:
    # 同期コンテキスト（Celery）
    async_to_sync(self.channel_layer.group_send)(...)
```

**重要な変更点**:
- `send_async()` 内に try-except を追加
- タスク内の例外を捕捉してログ出力
- "Task exception was never retrieved" 警告を防止
- 呼び出し元には例外が伝播しない（通知失敗でもメイン処理は継続）

**メリット**:
1. 同期コンテキスト（Celery）: `async_to_sync()` を使用
2. 非同期コンテキスト（WebSocket）: `asyncio.create_task()` を使用
3. 通知がドロップされない

## PostLog フィールド名エラー

### 問題

`post_log.save(update_fields=['duration'])` を呼び出していたが、実際のフィールド名は `duration_seconds`。

```python
class PostLog(models.Model):
    duration_seconds = models.IntegerField(...)  # ✅ 正しいフィールド名
    
    def calculate_duration(self):
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
            self.save(update_fields=['duration_seconds'])  # ✅
```

### 修正

```python
# 修正前
post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration'])  # ❌

# 修正後
post_log.save(update_fields=['status', 'error_message', 'completed_at', 'duration_seconds'])  # ✅
```

**修正箇所**:
- apps/blog/tasks.py:274 (タイトル・本文欠如)
- apps/blog/tasks.py:307 (アカウント無効)

## テスト改善

### 1. パス問題の修正

すべてのテストファイルで `/app` のハードコードを相対パスに変更：

```python
# 修正前
sys.path.insert(0, '/app')  # ❌ Docker環境のみ

# 修正後
from pathlib import Path
repo_root = Path(__file__).resolve().parents[1]  # ✅ 相対パス
sys.path.insert(0, str(repo_root))
```

**修正ファイル**:
- tests/test_async_notification.py
- tests/test_early_validation.py
- tests/test_nicedit_implementation.py
- tests/test_postlog_save.py

### 2. select_related() のモック修正

`BlogPost.objects.select_related('user', 'user__salon_board_account').get(id=post_id)` を正しくモック：

```python
# 修正前: get() だけをモック
with patch('apps.blog.tasks.BlogPost.objects.get') as mock_get_post:
    mock_get_post.return_value = mock_post  # ❌ select_related() が呼ばれない

# 修正後: select_related().get() のチェーンをモック
with patch('apps.blog.tasks.BlogPost.objects') as mock_objects:
    mock_select_related = Mock()
    mock_select_related.get.return_value = mock_post
    mock_objects.select_related.return_value = mock_select_related  # ✅
```

### 3. テスト結果

#### test_async_notification.py - 4/4 tests PASSED
- ✅ Sync Context: Celery workers use async_to_sync
- ✅ Async Context: WebSocket consumers use asyncio.create_task
- ✅ Mixed Context: Rapid notifications work correctly
- ✅ Async Error Handling: Exceptions in async tasks are caught and logged

#### test_postlog_save.py - 2/2 tests PASSED
- ✅ Missing content validation: post_log.save() called with duration_seconds
- ✅ Inactive account validation: post_log.save() called with duration_seconds
- ✅ Database operations BEFORE notifications

#### test_nicedit_implementation.py - 4/4 tests PASSED
- ✅ Selector definitions
- ✅ Cursor control (contenteditable div)
- ✅ Content fill strategy
- ✅ Success detection

## エラー処理のベストプラクティス

### 1. データベース操作を先に実行

```python
# ✅ Good
try:
    # データベース操作
    post.save(...)
    post_log.save(...)
except Exception as db_error:
    logger.error(...)

try:
    # 通知送信
    notifier.send_failed(...)
except Exception as notif_error:
    logger.error(...)
```

### 2. すべての操作に try-except

- データベース操作の失敗が通知送信をブロックしない
- 通知送信の失敗がデータベース保存をブロックしない

### 3. 正しいフィールド名を使用

- モデル定義を確認: `PostLog.duration_seconds`
- `calculate_duration()` メソッドを確認
- `update_fields` リストに正しい名前を指定

### 4. 早期バリデーションでも post_log.save()

- タイトル・本文欠如
- アカウント無効
- その他の早期エラー

すべてのケースで `post_log.save()` を呼び出し、フロントエンドから失敗理由を参照可能にする。

## 参考

- Django Channels: async_to_sync, sync_to_async
- asyncio: create_task, get_running_loop
- Django ORM: update_fields, select_related
- unittest.mock: patch, Mock
