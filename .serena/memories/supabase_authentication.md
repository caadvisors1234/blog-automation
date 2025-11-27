# Supabase認証実装

## 実装日
2025年11月27日

## ステータス
✅ **実装完了・動作確認済み**（2025年11月27日 23:22）

## 概要
Supabase認証を使用したメール/パスワードベースの認証システムを実装。管理者がSupabaseでユーザーを作成し、そのユーザーがログインできるクローズドアプリケーション。

## アーキテクチャ

### フロントエンド（templates/accounts/login.html）
- Supabase JS SDK v2（CDN経由）
- `signInWithPassword()`でSupabase認証
- 成功したらJWTトークンをバックエンドに送信
- エラーハンドリング、ローディング状態、ユーザーフレンドリーなエラーメッセージ

### バックエンド（apps/accounts/views.py）
- `login_view`: ログインフォーム表示、Supabase設定を渡す
- `supabase_login_view`: JWTトークン検証、Djangoセッション作成
  - JWTトークンを検証（`verify_supabase_token()`）
  - `supabase_user_id`でユーザー取得、存在しなければ自動作成
  - Djangoセッションを作成（`auth_login()`）
  - セッション有効期限の設定（remember me機能）

### URLルーティング（apps/accounts/template_urls.py）
- `/accounts/login/`: ログインフォーム
- `/accounts/login/supabase/`: Supabaseログインエンドポイント（POST）

### 既存機能との統合
- `SupabaseAuthMiddleware`: JWTトークン検証（既存、変更なし）
- `SupabaseAuthBackend`: Supabase認証バックエンド（既存、変更なし）
- `verify_supabase_token()`: JWT検証ユーティリティ（既存、変更なし）

## セキュリティ

### JWT検証
- HS256アルゴリズム
- 有効期限チェック
- `SUPABASE_JWT_SECRET`で署名検証

### セッション管理
- Django標準のセッション機能
- CSRF保護（Djangoデフォルト）
- Remember me機能（セッション有効期限の設定）

### パスワード管理
- Supabase側でbcryptハッシュ化
- Djangoには平文パスワードを保存しない

## 環境変数

`.env`ファイルに以下が必要:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

## ユーザー作成方法

### Supabaseダッシュボード（推奨）
1. Authentication → Users → Add User
2. メール/パスワードを入力
3. Auto Confirm User: ON
4. Create User

### Supabase CLI
```bash
supabase auth signup --email user@example.com --password securepassword123
```

## 実装ファイル

### フロントエンド
- `templates/accounts/login.html`: ログインフォーム、Supabase認証ロジック

### バックエンド
- `apps/accounts/views.py`: `login_view`, `supabase_login_view`
- `apps/accounts/template_urls.py`: URLルーティング
- `apps/accounts/utils.py`: `verify_supabase_token()`（既存）
- `apps/accounts/backends.py`: `SupabaseAuthBackend`（既存）
- `apps/accounts/middleware.py`: `SupabaseAuthMiddleware`（既存）

### ドキュメント
- `docs/SUPABASE_AUTH_SETUP.md`: 詳細なセットアップガイド

## テスト方法

1. Supabaseでユーザーを作成
2. `http://localhost:8000/accounts/login/`にアクセス
3. メール/パスワードを入力してログイン
4. ダッシュボードにリダイレクトされることを確認

## トラブルシューティング

### ログインできない
- ブラウザコンソールでエラー確認
- `docker-compose logs -f web`でDjangoログ確認
- Supabaseダッシュボードでユーザーの存在を確認

### JWT検証エラー
- `SUPABASE_JWT_SECRET`が正しいか確認
- アプリケーション再起動: `docker-compose restart web`

### CORS エラー
- Supabaseダッシュボード → Settings → API
- CORS Allowed Originsに`http://localhost:8000`を追加

## 重要な技術ポイント

### JWT Audience検証の無効化（最重要）
`apps/accounts/utils.py`の`verify_supabase_token()`で`verify_aud: False`を設定。
Supabaseトークンの`"aud": "authenticated"`クレームをスキップすることで検証成功。

### トラブルシューティング履歴
- **問題**: `ERROR: Invalid JWT token: Invalid audience`
- **解決**: `verify_aud: False`を追加（2025-11-27）
- **結果**: JWT検証成功、ログイン完動

## 参考資料
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Supabase JS signInWithPassword](https://supabase.com/docs/reference/javascript/auth-signinwithpassword)
- `docs/SUPABASE_AUTH_SETUP.md`: 詳細ガイド
- `docs/SUPABASE_AUTH_IMPLEMENTATION_SUMMARY.md`: 実装サマリー
