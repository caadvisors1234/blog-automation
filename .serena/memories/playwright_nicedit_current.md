# Playwright nicEdit 実装修正（最新）

## 方針
- nicEdit 前提の単一路線に簡素化（contenteditable フォールバックや textarea フォールバックは廃止）。
- 画像挿入順を強制制御：アップロードごとに data-upload-seq を付与し、編集領域末尾に append し直す。
- nicEdit が利用できない場合は例外を投げて明示失敗。

## 主要変更（2025-11-26）
- `apps/blog/salon_board_client.py`
  - 未使用 `Browser` import を削除。
  - `_fill_content_with_images`: nicEditor API のみ使用。プレースホルダを順に処理し、各画像挿入後に `_move_new_image_to_end` で末尾へ移動。
  - `_move_new_image_to_end(seq)`: data-upload-seq が未設定の img を検出し末尾へ移動。見つからない場合は最後の img を再度末尾に付けるフォールバック。
  - nicEdit 不可時のフォールバックは廃止し、`SALONBoardError` を送出。
  - 画像アップロード処理のデバッグログ（開く/ファイル設定/サムネ/送信/モーダル閉鎖）を簡潔に維持。
- `config/settings.py`
  - ログファイルのレベルを INFO に戻して運用。

## 運用上の要点
- ブログ本文には挿入したい枚数分の `{{image_n}}` プレースホルダを必ず含める（欠けたプレースホルダの画像は挿入されない）。
- nicEdit の編集領域は `div.nicEdit-main[contenteditable='true']`; カーソルは画像挿入前後に末尾へ移動させるが、最終的な順序は `_move_new_image_to_end` で担保。
- nicEdit が無い環境では例外となるため、実行前にページが nicEdit をロードしていることが前提。
