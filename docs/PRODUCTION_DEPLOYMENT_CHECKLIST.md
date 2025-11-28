# 本番環境デプロイチェックリスト（2025-XX 更新）

## デプロイ前の必須タスク

### 1. セキュリティ設定

#### 環境変数の設定
- [ ] `.env`ファイルを本番環境の環境変数管理システムに移行
  - Docker Secrets、AWS Secrets Manager、GCP Secret Manager等を使用
- [ ] `DEBUG=False`に設定
- [ ] `SECRET_KEY`を本番用の強力なキーに変更
- [ ] `ALLOWED_HOSTS`を本番ドメインに設定（例: `blog-automation.ai-beauty.tokyo`）
- [ ] `CSRF_TRUSTED_ORIGINS`に本番URLを追加（例: `https://blog-automation.ai-beauty.tokyo`）

#### HTTPS設定
- [ ] SSL証明書の取得と設定（Let's Encrypt推奨）
- [ ] `SECURE_SSL_REDIRECT = True`が有効になっていることを確認
- [ ] `SESSION_COOKIE_SECURE = True`が有効になっていることを確認
- [ ] `CSRF_COOKIE_SECURE = True`が有効になっていることを確認
- [ ] HSTS設定が有効になっていることを確認

### 2. Supabase設定

#### ダッシュボードでの設定
- [ ] Supabaseプロジェクトが本番環境用に設定されている
- [ ] メールサインアップを無効化（Authentication → Providers → Email → Enable Email Signup: OFF）
- [ ] パスワードポリシーを設定（Minimum Password Length: 8文字以上）
- [ ] パスワード強度要求を有効化
- [ ] JWT有効期限の設定確認（デフォルト: 1時間）

#### 環境変数の確認
- [ ] `SUPABASE_URL`が正しく設定されている
- [ ] `SUPABASE_KEY`（Anon Key）が正しく設定されている
- [ ] `SUPABASE_SERVICE_ROLE_KEY`が正しく設定されている
- [ ] `SUPABASE_JWT_SECRET`が正しく設定されている

### 3. データベース設定

#### マイグレーション
- [ ] 本番データベースで全マイグレーションを実行
  ```bash
  python manage.py migrate
  ```
- [ ] マイグレーション履歴の確認
  ```bash
  python manage.py showmigrations
  ```

#### 管理者アカウント
- [ ] スーパーユーザーを作成
  ```bash
  python manage.py createsuperuser
  ```
- [ ] Supabaseダッシュボードで対応するSupabaseユーザーを作成

### 4. 静的ファイルとメディア

- [ ] 静的ファイルを収集（イメージビルドで実行されるが念のため確認）
  ```bash
  python manage.py collectstatic --noinput
  ```
- [ ] メディアファイルのストレージ設定（AWS S3、GCS等）
- [ ] 静的ファイルのCDN設定（CloudFlare、AWS CloudFront等）

### 5. 依存パッケージ

- [ ] requirements.txtの全パッケージがインストールされている
  ```bash
  pip install -r requirements.txt
  ```
- [ ] `django-ratelimit==4.1.0`がインストールされている

### 6. ログ設定とモニタリング

#### ログ設定
- [ ] ログレベルを本番環境用に設定（INFO以上推奨）
- [ ] ログファイルのローテーション設定
- [ ] エラーログの保存先設定

#### モニタリング（推奨）
- [ ] Sentryなどのエラートラッキングツールの設定
- [ ] Prometheusなどのメトリクス収集ツールの設定
- [ ] アラート通知の設定

### 7. キャッシュとパフォーマンス

- [ ] Redisが本番環境で正常に動作している
- [ ] Celeryワーカーが起動している
- [ ] Celery Beatが起動している（スケジュールタスク用）

### 8. レート制限

- [ ] レート制限が有効になっていることを確認
  - ログインエンドポイント: 5回/分
- [ ] Redisキャッシュが正常に動作している

## デプロイ後の確認タスク

### 1. 認証機能の動作確認

- [ ] ログインページにアクセスできる（https://your-domain.com/accounts/login/）
- [ ] Supabaseで作成したユーザーでログインできる
- [ ] ログイン成功後、ダッシュボードにリダイレクトされる
- [ ] ログアウト機能が正常に動作する
- [ ] セッションが正しく維持される

### 2. セキュリティチェック

- [ ] HTTPSでアクセスできる
- [ ] HTTPからHTTPSへ自動リダイレクトされる
- [ ] HSTS設定が有効になっている（ブラウザのDevToolsで確認）
- [ ] CSRFトークンが正しく動作している
- [ ] レート制限が機能している（連続ログイン試行でテスト）

### 3. ログの確認

- [ ] アプリケーションログが正常に出力されている
- [ ] エラーログが記録されている
- [ ] 監査ログ（LoginAttempt）が記録されている
  - Django管理画面で確認: /admin/accounts/loginattempt/

### 4. パフォーマンステスト

- [ ] ページ読み込み速度が適切
- [ ] データベースクエリが最適化されている
- [ ] 静的ファイルが正しく配信されている

## Docker/Compose 運用メモ
- ベース `docker-compose.yml` はポート公開なし（NPM 経由でアクセス）。
- ローカル開発や手動確認は `docker-compose.override.yml` を併用し、`18001:8000` で Web を公開。
- 共有ネットワーク: `app-network`（事前に作成 or NPM で作成済みのものを再利用）。
- `web` は Gunicorn + Uvicorn worker（ASGI）、静的配信は WhiteNoise を使用。

### 5. バックアップ設定

- [ ] データベースの自動バックアップが設定されている
- [ ] バックアップの復元テストを実施
- [ ] メディアファイルのバックアップが設定されている

## Supabase認証関連の注意事項

### ユーザー作成方法

本番環境では管理者のみがユーザーを作成できます:

1. **Supabaseダッシュボードで作成**（推奨）
   ```
   Authentication → Users → Add User
   - Email: user@example.com
   - Password: 強力なパスワード
   - Auto Confirm User: ON
   ```

2. **初回ログイン**
   - ユーザーがログインすると、Djangoデータベースに自動的にユーザーが作成されます
   - `LoginAttempt`テーブルにログイン履歴が記録されます

### トラブルシューティング

#### ログインできない場合

1. **Supabaseユーザーの確認**
   - Supabaseダッシュボードでユーザーが存在するか確認
   - Email Confirmedがtrueになっているか確認

2. **JWT Secretの確認**
   ```bash
   # Supabaseダッシュボード
   Project Settings → API → JWT Settings → JWT Secret
   ```

3. **ログの確認**
   ```bash
   # Docker環境
   docker-compose logs -f web | grep -E "(JWT|token|Supabase|login)"

   # 成功時のログ例:
   # INFO - JWT token verified successfully. User ID: xxx
   # INFO - Django session created for user: username
   ```

4. **レート制限の確認**
   - 短時間に複数回ログイン試行していないか確認
   - 制限されている場合は数分待つか、Redisキャッシュをクリア

#### エラー「トークンの検証に失敗しました」

- JWT Secretが正しく設定されているか確認
- Supabaseプロジェクトが正しいか確認
- トークンの有効期限が切れていないか確認

## セキュリティベストプラクティス

### 定期的な確認事項

- [ ] 依存パッケージの脆弱性チェック
  ```bash
  pip list --outdated
  pip-audit  # pip install pip-audit
  ```
- [ ] ログイン試行の監視（LoginAttemptテーブル）
- [ ] 不審なIPアドレスからのアクセス確認
- [ ] SSL証明書の有効期限確認

### アクセス制限

- [ ] Django管理画面へのアクセスをIP制限（推奨）
- [ ] Supabaseダッシュボードへのアクセスを制限
- [ ] データベースへの直接アクセスを制限

## ロールバック計画

デプロイに問題が発生した場合:

1. **アプリケーションのロールバック**
   - 前のバージョンのコンテナイメージにロールバック
   - または、前のGitコミットにロールバック

2. **データベースのロールバック**
   ```bash
   # マイグレーションを元に戻す
   python manage.py migrate accounts 0002  # 前のマイグレーション番号
   ```

3. **バックアップからの復元**
   - データベースバックアップから復元
   - 環境変数を元の設定に戻す

## 連絡先とドキュメント

- プロジェクトドキュメント: `docs/`
- Supabase認証ドキュメント: `docs/SUPABASE_AUTH_SETUP.md`
- トラブルシューティング: `docs/TROUBLESHOOTING_JWT.md`
- 実装サマリー: `docs/SUPABASE_AUTH_IMPLEMENTATION_SUMMARY.md`

## デプロイ完了後

全てのチェックリストが完了したら:

- [ ] デプロイ日時を記録
- [ ] デプロイ担当者を記録
- [ ] デプロイしたバージョン/コミットハッシュを記録
- [ ] 問題が発生した場合の連絡先を確認
- [ ] ステークホルダーにデプロイ完了を通知

---

**最終更新日**: 2025年11月27日
**作成者**: Claude Code
**バージョン**: 1.0.0
