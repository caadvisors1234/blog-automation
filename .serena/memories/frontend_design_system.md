# blog-automation フロントエンドデザインシステム

## デザインコンセプト: Focus & Transparency (2025-11-25)
- 視覚的ノイズを排除し、コンテンツと機能性が浮かび上がるUI
- モノクロームベース（gray系 90%）+ 機能的アクセントカラー（pink系）
- フラットデザイン（box-shadow削除、ホバー時は背景色変更のみ）

## Tailwind CSS 構成

### ビルドシステム
- `package.json`: npm依存関係、ビルドスクリプト
- `tailwind.config.js`: カスタム設定
- `static/css/input.css`: Tailwindディレクティブ + @layer定義
- `static/css/output.css`: ビルド済み・最適化済みCSS

### ビルドコマンド
```bash
npm run watch:css   # 開発時（変更監視）
npm run build:css   # 本番ビルド（最適化・圧縮）
```

### カラーパレット
- **gray**: 50-950（UIの90%）
- **pink**: 50-900（アクション要素のみ）
- 機能色: red（エラー）, green（成功）, yellow（警告）, blue（情報）

### タイポグラフィ階層（4段階）
- `text-display`: 2rem/1.2 600（ページタイトル）
- `text-title`: 1.25rem/1.4 500（セクションヘッダー）
- `text-body`: 0.9375rem/1.6 400（本文）
- `text-caption`: 0.8125rem/1.5 400（キャプション）

### コンポーネントクラス
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`
- `.card`, `.card-interactive`
- `.badge-draft`, `.badge-generating`, `.badge-ready`, `.badge-publishing`, `.badge-published`, `.badge-failed`
- `.link`, `.focus-ring`, `.progress-bar`

## テンプレート構造
```
templates/
├── base.html（ベーステンプレート）
├── dashboard.html
├── accounts/
│   ├── login.html
│   └── settings.html
├── blog/
│   ├── list.html, create.html, detail.html
│   ├── edit.html, delete_confirm.html, history.html
└── errors/
    ├── 404.html, 500.html, 503.html
```

## JavaScript
- `static/js/main.js`: 画像プレビュー、フォームバリデーション、API呼び出し
- `static/js/websocket.js`: WebSocket接続、進捗更新、トースト通知
