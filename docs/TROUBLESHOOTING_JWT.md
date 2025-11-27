# JWT認証トラブルシューティングガイド

## 問題: 「トークンの検証に失敗しました」エラー

ログイン時に「トークンの検証に失敗しました」というエラーが表示される場合、JWT Secretの設定に問題がある可能性があります。

## 原因

Djangoバックエンドが使用している`SUPABASE_JWT_SECRET`が、Supabaseプロジェクトの実際のJWT Secretと一致していない。

## 解決手順

### 1. Supabaseダッシュボードで正しいJWT Secretを確認

1. [Supabase Dashboard](https://supabase.com/dashboard)にログイン
2. あなたのプロジェクトを選択
3. 左サイドバーから **Settings** (⚙️) をクリック
4. **API** セクションを選択
5. **JWT Settings** セクションを探す
6. **JWT Secret** をコピー

![JWT Secret location](https://supabase.com/docs/img/guides/api/api-settings.png)

**重要**: 以下の違いに注意してください:
- ❌ `service_role` secret (これは別物)
- ❌ `anon` / `public` key (これも別物)
- ✅ **JWT Secret** (これが必要)

### 2. .envファイルを更新

`.env`ファイルを開き、`SUPABASE_JWT_SECRET`を更新:

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-actual-jwt-secret-here  # ← これを更新
```

**重要**:
- JWT Secretはbase64エンコードされた長い文字列です（例: `O6IwEr+1/HJ6VNO9sPiK...`）
- 先頭・末尾にスペースがないことを確認
- 引用符は不要

### 3. Dockerコンテナを再起動

```bash
docker-compose restart web
```

または、完全に再ビルド:

```bash
docker-compose down
docker-compose up -d --build
```

### 4. 設定を確認

```bash
docker-compose exec web python test_jwt_verification.py
```

このスクリプトは以下を確認します:
- 環境変数が正しく読み込まれているか
- JWT Secretの長さ
- （オプション）実際のトークンの検証

### 5. ブラウザでログインをテスト

1. ブラウザコンソールを開く（F12 → Console）
2. `http://localhost:8000/accounts/login/`にアクセス
3. メール/パスワードを入力してログイン
4. コンソールに以下の情報が表示されます:
   ```
   Supabase authentication successful
   Token length: XXX
   Token (first 50 chars): eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOi...
   JWT algorithm: HS256
   JWT header: {alg: "HS256", typ: "JWT"}
   ```

5. Djangoログを確認:
   ```bash
   docker-compose logs -f web
   ```

   成功時のログ:
   ```
   INFO - JWT token verified successfully. User ID: xxx, Email: user@example.com
   INFO - Django session created for user: username
   ```

   失敗時のログ:
   ```
   ERROR - Invalid JWT token: Signature verification failed
   ```

## よくある問題

### 問題1: "Signature verification failed"

**原因**: JWT Secretが間違っている

**解決策**:
1. Supabaseダッシュボードから正しいJWT Secretをコピー
2. `.env`ファイルを更新
3. Dockerコンテナを再起動

### 問題2: "Token has expired"

**原因**: トークンの有効期限が切れている

**解決策**:
- これは正常な動作です
- もう一度ログインしてください
- Supabaseのトークンは通常1時間有効です

### 問題3: トークンのアルゴリズムがRS256/ES256

**原因**: Supabaseプロジェクトが非対称鍵を使用している（新しいプロジェクト）

**解決策**:
現在の実装はHS256のみサポートしています。RS256/ES256をサポートするには、以下の変更が必要です:

1. JWKSエンドポイントから公開鍵を取得
2. `PyJWT`ライブラリを使用してRS256検証
3. `apps/accounts/utils.py`の`verify_supabase_token()`を更新

詳細は以下を参照:
- [Supabase JWT Documentation](https://supabase.com/docs/guides/auth/jwts)
- [PyJWT RS256 Example](https://pyjwt.readthedocs.io/en/stable/usage.html#encoding-decoding-tokens-with-rs256-rsa)

## デバッグ用のテストスクリプト

プロジェクトルートに`test_jwt_verification.py`があります。

使い方:

```bash
# コンテナ内で実行
docker-compose exec web python test_jwt_verification.py

# 実際のトークンをテスト
docker-compose exec -it web python test_jwt_verification.py
# プロンプトでトークンを貼り付け
```

このスクリプトは:
- 環境変数の確認
- トークンのデコード（検証なし）
- アルゴリズムの確認
- トークンの検証
- 詳細なエラーメッセージ

## まだ解決しない場合

### 1. ログの詳細を確認

```bash
docker-compose logs -f web | grep -E "(JWT|token|Supabase|login)"
```

### 2. Supabase Authログを確認

Supabase Dashboard → Authentication → Logs で認証リクエストを確認できます。

### 3. ブラウザのNetwork タブを確認

1. F12 → Network
2. ログインを試行
3. `token` リクエストを確認
4. Responseにaccess_tokenがあることを確認
5. そのトークンをコピーして`test_jwt_verification.py`でテスト

## 参考資料

- [Supabase JWT Documentation](https://supabase.com/docs/guides/auth/jwts)
- [Supabase API Settings](https://supabase.com/docs/guides/api)
- [JWT.io Debugger](https://jwt.io/) - トークンのデコードとデバッグ
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)

## 連絡先

問題が解決しない場合:
1. 上記のデバッグ手順の出力をすべて収集
2. Supabaseダッシュボードのスクリーンショット
3. エラーログの全文
4. これらを管理者に報告
