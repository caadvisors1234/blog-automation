# 02. 自動化実装詳細設計書 (Automation Implementation Spec)

## 1. 概要
本ドキュメントは、Playwright を用いた SALON BOARD 自動操作の具体的実装仕様を定義する。
開発者はこのセレクタ定義とロジックフローを厳守して実装すること。

---

## 2. セレクタ定義 (selectors.yaml)

HTML解析に基づく最新のセレクタ。実装時は外部YAMLファイルとして読み込むか、定数クラスとして定義する。

```yaml
salon_board:
  base_url: "<https://salonboard.com>"

  # --- ログイン関連 ---
  login:
    url: "<https://salonboard.com/login/>"
    user_input: "input[name='userId']"
    password_input: "#jsiPwInput"      # JSで制御されている場合がある
    password_input_alt: "input[name='password']"
    submit_btn: "#idPasswordInputForm > div > div > a"
    submit_btn_alt: "a.common-CNCcommon__primaryBtn.loginBtnSize"

  # --- 妨害要素（CSSでdisplay:noneにする対象） ---
  blockers:
    - ".karte-widget__container"
    - "[class*='_reception-Skin']"
    - "[class*='_reception-MinimumWidget']"
    - "[id^='karte-']"

  # --- ロボット検知（出現したらエラー中断） ---
  robot_detection:
    selectors:
      - "iframe[src*='recaptcha']"
      - "div.g-recaptcha"
      - "img[alt*='認証']"
      - "form[action*='auth']"

  # --- ナビゲーション ---
  nav:
    # 複数店舗選択画面
    # テーブル内の「ID」列、またはリンクのID属性を使って特定する
    salon_table: "#biyouStoreInfoArea"

    # メニュー遷移
    publish_manage: "#globalNavi > ul.common-CLPcommon__globalNavi > li:nth-child(2) > a" # 掲載管理
    blog_menu: "#cmsForm > div > div > ul > li:nth-child(9) > a" # ブログ
    new_post_btn: "#newPosts" # 新規投稿

  # --- ブログ投稿フォーム ---
  form:
    stylist: "select#stylistId"     # T番号 (value属性) で選択
    category: "select#blogCategoryCd" # 固定: BL02 (おすすめメニューなど)
    title: "input#blogTitle"

    # リッチエディタ (nicEdit)
    editor_iframe: "iframe[id^='nicEdit']"
    # 操作対象は iframe.contentDocument.body

    # 画像アップロード
    image:
      trigger_btn: "a#upload"
      modal: "div.imageUploaderModal"
      file_input: "input#sendFile"
      thumbnail: "img.imageUploaderModalThumbnail" # 完了判定用
      submit_btn: "input.imageUploaderModalSubmitButton.isActive" # 活性化状態でクリック

    # クーポン選択
    coupon:
      trigger_btn: "a.jsc_SB_modal_trigger"
      modal: "div#couponWrap"
      # 部分一致検索対象
      label_list: "div#couponWrap label"
      setting_btn: "a.jsc_SB_modal_setting_btn"

    # 確認・完了アクション
    actions:
      confirm_btn: "a#confirm"
      reflect_btn: "a#reflect"   # 「登録・反映する」
```
---

## 3. 実装ロジック詳細

### 3.1 共通処理: 妨害要素の排除と検知

すべてのページ遷移 (`page.goto`, `page.click` による遷移) の直後に、以下の処理を実行する。

1. **ロボット検知チェック**:
`robot_detection.selectors` のいずれかが表示 (`visible`) されているか確認。検知された場合は `RobotDetectionError` を送出して処理を中断する。
2. **Widget非表示化**:
`page.add_style_tag` を使用し、`blockers` に定義された要素を `display: none !important;` に設定するCSSを注入する。

### 3.2 ログインと店舗選択

1. **ログイン**: ID/PASSを入力しログイン。
2. **店舗選択（複数店舗アカウントの場合）**:
    - ログイン後、URLが店舗トップでない（店舗選択画面である）場合。
    - 設定された「サロンID (例: H000123456)」を使用し、対象店舗をクリックする。
    - **セレクタ戦略**:
        
        ```python
        # target_salon_id = "H000xxxxxx"
        # ID属性がサロンIDと一致するaタグをクリック
        page.click(f"a[id='{target_salon_id}']")
        
        ```
        
    - ※テーブル内の構造が変わっても、`id="H..."` が維持されている限りこのセレクタが最も堅牢である。

### 3.3 クーポン選択（部分一致・First Match）

1. 「クーポンを追加」ボタンをクリックし、モーダルを表示。
2. Playwrightのフィルタ機能を使用。
    
    ```python
    # target_coupon_name = "カット＋カラー"
    # テキストを含むラベルを検索し、最初の要素をクリック
    page.locator("div#couponWrap label").filter(has_text=target_coupon_name).first.click()
    
    ```
    
3. 「設定する」ボタンをクリック。

### 3.4 本文入力と画像挿入（カーソル制御必須）

nicEditは `iframe` 内の `body` を編集する。画像アップロード時、フォーカス位置に画像が挿入されるため、**明示的なカーソル移動**が必要である。
すべての操作は **iframeのコンテキスト内** で実行し、`window` や `document` オブジェクトも iframe 内のものを参照する必要がある。

**処理フロー:**
本文データを分割し、`[テキストブロックA, 画像1, テキストブロックB...]` の順で処理する。

### ステップごとの操作:

1. **iframe ロケータの取得**:
    
    ```python
    # iframeを特定
    editor_frame = page.frame_locator("iframe[id^='nicEdit']")
    # iframe内のbodyを特定
    editor_body = editor_frame.locator("body")
    
    ```
    
2. **テキスト追記 (iframe内で実行)**:
    - `editor_body` に対する `evaluate` は、自動的にiframeコンテキスト内で実行される。
    
    ```python
    text_content = "追記したいテキスト<br>"
    # el は iframe内の body 要素を指す
    editor_body.evaluate(f"el => el.innerHTML += '{text_content}'")
    
    ```
    
3. **カーソルを末尾へ移動 (iframe内で実行)**:
    - 画像アップロードボタンを押す**前**に、カーソルが文頭や意図しない位置にないことを保証する。
    - 以下のJavaScriptロジックをPython変数として定義し、実行する。
    - **重要**: `body.ownerDocument` を経由して、確実にiframe内の `document` と `window` を取得する。
    
    ```python
    js_move_cursor = """
    (body) => {
        const doc = body.ownerDocument;
        const win = doc.defaultView || doc.parentWindow;
    
        body.focus();
        const range = doc.createRange();
        const selection = win.getSelection();
    
        range.selectNodeContents(body);
        range.collapse(false); // false = 末尾
    
        selection.removeAllRanges();
        selection.addRange(range);
    }
    """
    # iframe内のbodyに対して実行
    editor_body.evaluate(js_move_cursor)
    
    ```
    
4. **画像アップロード**:
    - `page.click("a#upload")` (これはメインフレーム上の操作)
    - `page.set_input_files("input#sendFile", file_path)`
    - `page.wait_for_selector("img.imageUploaderModalThumbnail")` (サムネイル待機)
    - `page.click("input.imageUploaderModalSubmitButton.isActive")`
    - モーダルが消えるのを待つ (`page.wait_for_selector("div.imageUploaderModal", state="hidden")`)。
5. **カーソルを末尾へ移動 (再実行)**:
    - 画像挿入後、フォーカス位置リセット防止のため、再度手順3の `js_move_cursor` を実行する。
    
    ```python
    editor_body.evaluate(js_move_cursor)
    
    ```
    
6. (次のテキストブロックへ進む)

### 3.5 完了処理

1. 「確認画面へ」をクリック。
2. エラー（入力不備のアラート等）がないか確認。
3. **「登録・反映する」 (`a#reflect`)** をクリック。
    - ※「登録・反映しない」ボタンと間違えないようID指定を徹底する。
4. 完了画面が表示されたら、`page.screenshot()` を実行し、ファイルパスを保存する。

---

## 4. 例外設計

以下の例外クラスを実装し、発生時は適切にログ出力・中断処理を行う。

- `LoginError`: ログイン失敗。
- `RobotDetectionError`: CAPTCHA検知。
- `SalonSelectionError`: 指定されたサロンIDが見つからない。
- `ElementNotFoundError`: 必須セレクタ（投稿ボタン等）が見つからない。
- `UploadError`: 画像アップロード処理のタイムアウト等。