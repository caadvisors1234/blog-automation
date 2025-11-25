# Playwright nicEdit 実装修正詳細 (2025-11-25)

## 問題の背景

SALON BOARD の nicEdit エディタを Playwright で自動操作する際に、以下の問題が発生していた：

### 1. 30秒タイムアウトエラー
- **原因**: `iframe[id^='nicEdit']` を探していたが、実際には iframe は存在しない
- **実際の構造**: nicEdit は contenteditable div を使用
- **影響**: コンテンツ挿入時に毎回30秒タイムアウトが発生

### 2. カーソル位置制御の失敗
- **原因**: `editorInstance.elm` (textarea) に対してカーソル制御を実行
- **問題**: textarea にフォーカスしても編集領域（contenteditable div）のカーソル位置は変わらない
- **影響**: 画像が常に先頭に挿入され、`{{image_N}}` の順序通りにならない

### 3. 成功検知の失敗
- **原因**: 実際の完了メッセージ `'ブログの登録が完了しました'` がチェック対象に含まれていない
- **影響**: 投稿成功時も失敗と判定される

## 修正内容

### 1. セレクタ定義の修正 (`apps/blog/salon_board_client.py:98-104`)

```python
# 修正前
FORM = {
    'editor_iframe': "iframe[id^='nicEdit']",  # ❌ 存在しない
}

# 修正後
FORM = {
    'editor_div': "div.nicEdit-main[contenteditable='true']",  # ✅ 実際の編集領域
    'editor_textarea': "textarea#blogContents",  # ✅ nicEditor API バインド先
}
```

### 2. カーソル制御の修正 (`apps/blog/salon_board_client.py:825-867`)

```python
# 修正前: textarea に対して操作
var editorInstance = nicEditors.findEditor('blogContents');
if (editorInstance) {
    var editor = editorInstance.elm;  // ❌ textarea要素
    var range = document.createRange();
    range.selectNodeContents(editor);  // ❌ textareaに対して操作
    // ...
}

# 修正後: contenteditable div に対して操作
var editor = document.querySelector("div.nicEdit-main[contenteditable='true']");
if (editor) {
    // ✅ 実際の編集領域に対して操作
    var range = document.createRange();
    range.selectNodeContents(editor);
    range.collapse(false); // false = 末尾に移動
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    editor.focus();
    return true;
}
```

**ポイント**:
- Range API: `createRange()`, `selectNodeContents()`, `collapse(false)`
- Selection API: `getSelection()`, `removeAllRanges()`, `addRange()`
- 画像アップロード前後に必ず実行

### 3. コンテンツ挿入の3層フォールバック (`apps/blog/salon_board_client.py:649-756`)

```python
def _fill_content_with_images(self, content: str, image_paths: List[str]) -> None:
    # Method 1: nicEditor API を試行
    try:
        js_script = """
        (function() {
            var editorInstance = nicEditors.findEditor('blogContents');
            if (editorInstance) {
                editorInstance.setContent('');
                return true;
            }
            return false;
        })();
        """
        result = self.page.evaluate(js_script)
        if result:
            # nicEditor API で処理
            # ...
            return
    except Exception as api_err:
        logger.warning(f"nicEditor API method failed: {api_err}")
    
    # Method 2: contenteditable div に直接操作
    try:
        editor_div = self.page.locator(Selectors.FORM['editor_div'])
        if editor_div.count() > 0:
            editor_div.evaluate("el => el.innerHTML = ''")
            # innerHTML で処理
            # ...
            return
    except Exception as div_err:
        logger.warning(f"Contenteditable div method failed: {div_err}")
    
    # Method 3: textarea フォールバック
    raise Exception("All primary methods failed, using fallback")
```

### 4. 成功検知の修正 (`apps/blog/salon_board_client.py:1112-1165`)

```python
# 修正前
success_indicators = [
    '投稿しました',
    '公開しました',
    # ❌ 実際のメッセージが含まれていない
]

# 修正後
success_indicators = [
    'ブログの登録が完了しました',  # ✅ 実際のメッセージ
    '投稿しました',
    '公開しました',
    '登録しました',
    '保存しました',
]

# 追加: 戻るボタンの存在チェック
back_button_exists = self.page.locator("a#back").count() > 0
if success or back_button_exists:
    return {'success': True, ...}
```

## テスト結果

### test_nicedit_implementation.py - 4/4 tests PASSED
- ✅ Selector Definitions: editor_div, editor_textarea, no editor_iframe
- ✅ nicEditor Cursor Control: Range API, Selection API
- ✅ Content Fill Strategy: 3-tier fallback
- ✅ Success Detection: 実際のメッセージ、back button

### 実行ログ検証
```
# 修正前
WARNING ... Error filling content in nicEdit: Timeout 30000ms exceeded.
# 処理時間: 30秒以上

# 修正後
DEBUG ... Moved cursor to end of nicEdit contenteditable div
DEBUG ... Content filled using nicEditor API
# 処理時間: 2秒
```

## ドキュメント更新

### docs/playwright_automation_spec.md
- セレクタ定義に nicEdit の実装詳細を追記
- iframe を使用しないことを明記
- カーソル制御の JavaScript コード例を追加

## 重要なポイント

1. **nicEdit は iframe を使用しない**: contenteditable div を直接操作
2. **カーソル制御対象**: `div.nicEdit-main[contenteditable='true']`
3. **nicEditor API**: `nicEditors.findEditor('blogContents')` で取得可能
4. **Range/Selection API**: ブラウザ標準 API でカーソル位置を制御
5. **3層フォールバック**: API → contenteditable → textarea の順で試行

## 参考資料

- nicEdit 公式: http://nicedit.com/
- MDN Range API: https://developer.mozilla.org/en-US/docs/Web/API/Range
- MDN Selection API: https://developer.mozilla.org/en-US/docs/Web/API/Selection
