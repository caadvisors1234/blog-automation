# Supabase認証セットアップガイド

## 概要

このアプリケーションはSupabase認証を使用してユーザーログインを管理します。管理者がSupabaseでユーザーを作成し、そのユーザーがメールアドレスとパスワードでログインできます。

## アーキテクチャ

### 認証フロー

1. **フロントエンド（ブラウザ）**
   - ユーザーがメール/パスワードを入力
   - Supabase JS SDKで`signInWithPassword()`を実行
   - 成功したらJWTアクセストークンを取得

2. **バックエンド（Django）**
   - JWTトークンを受け取り、検証
   - Djangoデータベースでユーザーを取得/作成
   - Djangoセッションを作成
   - 以降はセッションベース認証で動作

### セキュリティ

- **JWT検証**: HS256アルゴリズム、有効期限チェック
- **セッション管理**: Django標準のセッション機能
- **パスワードハッシュ**: Supabase側でbcryptを使用
- **CSRF保護**: Django標準設定

## セットアップ手順

### 1. Supabaseプロジェクト作成

1. [Supabase](https://supabase.com/)にログイン
2. 新しいプロジェクトを作成
3. プロジェクトの設定から以下の情報を取得:
   - **Project URL**: `https://your-project.supabase.co`
   - **Anon/Public Key**: `eyJhbGc...`（公開キー）
   - **Service Role Key**: `eyJhbGc...`（管理者キー、機密情報）
   - **JWT Secret**: プロジェクト設定 → API → JWT Settingsから取得

### 2. 環境変数設定

`.env`ファイルに以下を追加:

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

**重要**: `.env`ファイルは`.gitignore`に含まれています。本番環境では環境変数として設定してください。

### 3. Supabase認証設定

Supabaseダッシュボードで以下を設定:

#### 3.1 Email認証を有効化

1. Authentication → Providers → Email
2. **Enable Email Provider**: ONにする
3. **Confirm Email**: ONにする（推奨、メール確認必須）
   - OFFにすると、ユーザー作成後すぐにログイン可能
4. **Secure Email Change**: ONにする（推奨）

#### 3.2 サインアップ無効化（クローズドアプリ用）

管理者のみがユーザーを作成できるようにします:

1. Authentication → Providers → Email
2. **Enable Email Signup**: **OFF**にする

または、Supabase SQL EditorでRLSポリシーを設定:

```sql
-- パブリックサインアップを無効化
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- 管理者のみがユーザー作成可能
CREATE POLICY "Admin only can create users"
ON auth.users
FOR INSERT
TO service_role
WITH CHECK (true);
```

#### 3.3 パスワードポリシー設定

1. Authentication → Policies
2. **Minimum Password Length**: 8文字以上（推奨）
3. **Require Password Strength**: 有効化（推奨）

### 4. ユーザー作成方法

#### 方法1: Supabaseダッシュボード（推奨）

1. Authentication → Users → Add User
2. メールアドレスとパスワードを入力
3. **Auto Confirm User**: ONにする（メール確認をスキップ）
4. Create Userをクリック

#### 方法2: Supabase CLIまたはAPI

```bash
# Supabase CLIでユーザー作成
supabase auth signup --email user@example.com --password securepassword123

# または、curlでAPI呼び出し
curl -X POST 'https://your-project.supabase.co/auth/v1/admin/users' \
  -H "apikey: YOUR_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer YOUR_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "email_confirm": true
  }'
```

#### 方法3: Django管理画面（バックアップ）

Supabase認証が利用できない場合、Django管理画面でスーパーユーザーを作成:

```bash
docker-compose exec web python manage.py createsuperuser
```

### 5. 動作確認

#### 5.1 環境変数の確認

```bash
# Dockerコンテナ内で確認
docker-compose exec web python manage.py shell

>>> from django.conf import settings
>>> print(settings.SUPABASE_URL)
>>> print(settings.SUPABASE_KEY)
>>> print(settings.SUPABASE_JWT_SECRET)
```

すべての値が正しく表示されることを確認してください。

#### 5.2 ログインテスト

1. ブラウザで`http://localhost:8000/accounts/login/`にアクセス
2. Supabaseで作成したユーザーのメール/パスワードを入力
3. ログインボタンをクリック
4. ダッシュボードにリダイレクトされることを確認

#### 5.3 ログの確認

```bash
# Djangoログを確認
docker-compose logs -f web

# 成功時のログ例:
# INFO - Existing user logged in: username (supabase_id: abc123...)
# INFO - Django session created for user: username
```

## トラブルシューティング

### ログインできない

#### 1. Supabase設定を確認

```bash
# ブラウザのコンソールを開く（F12 → Console）
# エラーメッセージを確認
```

よくあるエラー:

- **Invalid login credentials**: メール/パスワードが間違っている、またはユーザーが存在しない
- **Email not confirmed**: メール確認が必要（Supabaseダッシュボードで手動確認）
- **User not found**: Supabaseにユーザーが存在しない

#### 2. JWT検証エラー

```bash
# Djangoログを確認
docker-compose logs -f web

# エラー例:
# ERROR - Login error: Token verification failed
```

原因:
- `SUPABASE_JWT_SECRET`が正しくない
- トークンの有効期限切れ
- トークンの形式が不正

解決方法:
1. `.env`ファイルの`SUPABASE_JWT_SECRET`を確認
2. Supabaseダッシュボードから正しいJWT Secretを取得
3. アプリケーションを再起動: `docker-compose restart web`

#### 3. CORS エラー

```
Access to fetch at 'https://your-project.supabase.co/auth/v1/token'
from origin 'http://localhost:8000' has been blocked by CORS policy
```

解決方法:
1. Supabaseダッシュボード → Settings → API
2. **CORS Allowed Origins**に`http://localhost:8000`を追加

### ユーザーが自動作成されない

Djangoのログを確認:

```bash
docker-compose logs -f web | grep "User created"
```

`User.DoesNotExist`エラーが出る場合:
- `supabase_user_id`フィールドが正しく保存されていない
- マイグレーションが実行されていない

解決方法:

```bash
# マイグレーション実行
docker-compose exec web python manage.py migrate

# データベースを確認
docker-compose exec web python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.all()
```

## セキュリティベストプラクティス

### 1. 環境変数の管理

- **絶対に**`.env`ファイルをGitにコミットしない
- 本番環境では環境変数として設定
- `SUPABASE_SERVICE_ROLE_KEY`は特に機密情報

### 2. JWT Secret の保護

- `SUPABASE_JWT_SECRET`は認証の要
- 定期的にローテーション（Supabaseダッシュボードから可能）

### 3. HTTPS の使用

- 本番環境では必ずHTTPSを使用
- Supabaseは自動的にHTTPS接続

### 4. セッション設定

`config/settings.py`で以下を確認:

```python
# セッション設定
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # JavaScriptからアクセス不可
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_COOKIE_AGE = 1209600  # 2 weeks
```

### 5. Rate Limiting

Supabaseは自動的にレート制限を実施:
- 認証エンドポイント: 30リクエスト/時間/IPアドレス

追加でDjango側でもレート制限を実装可能（django-ratelimitなど）。

## 参照

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Supabase JS Client](https://supabase.com/docs/reference/javascript/auth-signinwithpassword)
- [Django Authentication](https://docs.djangoproject.com/en/5.0/topics/auth/)
