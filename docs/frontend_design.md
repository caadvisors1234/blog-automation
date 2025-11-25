# 08. フロントエンド画面設計書 (Frontend Design Specification)

## 1. 概要
本ドキュメントは、HPBブログ自動化システムのフロントエンド画面設計を定義します。
Django Template + Tailwind CSSによるサーバーサイドレンダリングを基本とし、WebSocketでリアルタイム更新を実現します。

---

## 2. デザイン方針

### 2.1 UI/UXの原則
- **シンプル**: 必要最小限の操作で目的達成
- **直感的**: 説明不要で使える画面設計
- **レスポンシブ**: モバイル・タブレット・PCで最適表示
- **アクセシブル**: 視認性・操作性を重視

### 2.2 技術スタック
- **テンプレートエンジン**: Django Template
- **CSSフレームワーク**: Tailwind CSS 3.x
- **アイコン**: Heroicons（Tailwind標準）
- **フォント**: システムフォント
- **JavaScriptライブラリ**: Vanilla JS（最小限）

### 2.3 カラーパレット

```css
/* Tailwind CSS設定 */
:root {
  --color-primary: #3B82F6;    /* blue-500 */
  --color-secondary: #10B981;  /* green-500 */
  --color-danger: #EF4444;     /* red-500 */
  --color-warning: #F59E0B;    /* yellow-500 */
  --color-info: #06B6D4;       /* cyan-500 */
  --color-gray: #6B7280;       /* gray-500 */
}
```

---

## 3. 画面一覧

### 3.1 認証関連
1. ログイン画面（`/accounts/login/`）
2. サインアップ画面（`/accounts/signup/`）
3. ユーザー設定画面（`/accounts/settings/`）

### 3.2 ブログ投稿関連
4. ダッシュボード（`/`）
5. ブログ投稿一覧（`/blog/`）
6. ブログ新規作成（`/blog/create/`）
7. AI生成中画面（`/blog/{id}/generating/`）- 新規
8. 記事選択画面（`/blog/{id}/select/`）- 新規
9. ブログ詳細表示（`/blog/{id}/`）
10. 投稿履歴（`/blog/history/`）

---

## 4. 共通レイアウト

### 4.1 ベーステンプレート

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}HPBブログ自動化{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="{% static 'css/custom.css' %}">
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- ヘッダー -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex">
                    <!-- ロゴ -->
                    <div class="flex-shrink-0 flex items-center">
                        <a href="{% url 'dashboard' %}" class="text-xl font-bold text-blue-600">
                            HPBブログ自動化
                        </a>
                    </div>

                    <!-- ナビゲーション -->
                    {% if user.is_authenticated %}
                    <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
                        <a href="{% url 'dashboard' %}"
                           class="{% if request.resolver_match.url_name == 'dashboard' %}border-blue-500 text-gray-900{% else %}border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700{% endif %} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            ダッシュボード
                        </a>
                        <a href="{% url 'blog:list' %}"
                           class="{% if 'blog' in request.resolver_match.url_name %}border-blue-500 text-gray-900{% else %}border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700{% endif %} inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            ブログ投稿
                        </a>
                        <a href="{% url 'blog:history' %}"
                           class="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium">
                            投稿履歴
                        </a>
                    </div>
                    {% endif %}
                </div>

                <!-- ユーザーメニュー -->
                {% if user.is_authenticated %}
                <div class="flex items-center">
                    <div class="ml-3 relative">
                        <div class="flex items-center space-x-4">
                            <span class="text-sm text-gray-700">{{ user.username }}</span>
                            <a href="{% url 'accounts:settings' %}"
                               class="text-gray-500 hover:text-gray-700">
                                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                </svg>
                            </a>
                            <a href="{% url 'accounts:logout' %}"
                               class="text-gray-500 hover:text-gray-700">
                                ログアウト
                            </a>
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </nav>

    <!-- メッセージ表示 -->
    {% include 'includes/messages.html' %}

    <!-- メインコンテンツ -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {% block content %}{% endblock %}
    </main>

    <!-- フッター -->
    <footer class="bg-white border-t border-gray-200 mt-auto">
        <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            <p class="text-center text-sm text-gray-500">
                &copy; 2025 HPBブログ自動化システム
            </p>
        </div>
    </footer>

    {% block scripts %}{% endblock %}
</body>
</html>
```

### 4.2 メッセージ表示

```html
<!-- templates/includes/messages.html -->
{% if messages %}
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
    {% for message in messages %}
    <div class="rounded-md p-4 {% if message.tags == 'success' %}bg-green-50 border border-green-200{% elif message.tags == 'error' %}bg-red-50 border border-red-200{% elif message.tags == 'warning' %}bg-yellow-50 border border-yellow-200{% else %}bg-blue-50 border border-blue-200{% endif %}">
        <div class="flex">
            <div class="flex-shrink-0">
                {% if message.tags == 'success' %}
                <svg class="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                {% elif message.tags == 'error' %}
                <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                {% endif %}
            </div>
            <div class="ml-3">
                <p class="text-sm font-medium {% if message.tags == 'success' %}text-green-800{% elif message.tags == 'error' %}text-red-800{% elif message.tags == 'warning' %}text-yellow-800{% else %}text-blue-800{% endif %}">
                    {{ message }}
                </p>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endif %}
```

---

## 5. 各画面の詳細設計

### 5.1 ログイン画面

**パス**: `/accounts/login/`
**テンプレート**: `templates/accounts/login.html`

```html
{% extends 'base.html' %}

{% block title %}ログイン - HPBブログ自動化{% endblock %}

{% block content %}
<div class="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
        <div>
            <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
                アカウントにログイン
            </h2>
        </div>
        <form class="mt-8 space-y-6" method="POST">
            {% csrf_token %}
            <div class="rounded-md shadow-sm -space-y-px">
                <div>
                    <label for="email" class="sr-only">メールアドレス</label>
                    <input id="email" name="email" type="email" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                           placeholder="メールアドレス">
                </div>
                <div>
                    <label for="password" class="sr-only">パスワード</label>
                    <input id="password" name="password" type="password" required
                           class="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                           placeholder="パスワード">
                </div>
            </div>

            <div>
                <button type="submit"
                        class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    ログイン
                </button>
            </div>

            <div class="text-center">
                <a href="{% url 'accounts:signup' %}" class="font-medium text-blue-600 hover:text-blue-500">
                    アカウントを作成
                </a>
            </div>
        </form>
    </div>
</div>
{% endblock %}
```

**ワイヤーフレーム**:
```
┌─────────────────────────────────┐
│      ロゴ                       │
│                                 │
│   アカウントにログイン          │
│                                 │
│  ┌───────────────────────────┐  │
│  │ メールアドレス            │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ パスワード                │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │      ログイン             │  │
│  └───────────────────────────┘  │
│                                 │
│       アカウントを作成          │
└─────────────────────────────────┘
```

---

### 5.2 ダッシュボード

**パス**: `/`
**テンプレート**: `templates/dashboard.html`

```html
{% extends 'base.html' %}

{% block title %}ダッシュボード - HPBブログ自動化{% endblock %}

{% block content %}
<div class="px-4 py-6 sm:px-0">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">ダッシュボード</h1>

    <!-- 統計カード -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        <!-- 総投稿数 -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                総投稿数
                            </dt>
                            <dd class="text-2xl font-semibold text-gray-900">
                                {{ total_posts }}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>

        <!-- 今月の投稿数 -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                今月の投稿
                            </dt>
                            <dd class="text-2xl font-semibold text-gray-900">
                                {{ monthly_posts }}
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>

        <!-- 成功率 -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">
                                成功率
                            </dt>
                            <dd class="text-2xl font-semibold text-gray-900">
                                {{ success_rate }}%
                            </dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- クイックアクション -->
    <div class="bg-white shadow sm:rounded-lg">
        <div class="px-4 py-5 sm:p-6">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                クイックアクション
            </h3>
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <a href="{% url 'blog:create' %}"
                   class="relative block w-full border-2 border-gray-300 border-dashed rounded-lg p-6 text-center hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                    </svg>
                    <span class="mt-2 block text-sm font-medium text-gray-900">
                        新規ブログ作成
                    </span>
                </a>

                <a href="{% url 'blog:history' %}"
                   class="relative block w-full border-2 border-gray-300 border-dashed rounded-lg p-6 text-center hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span class="mt-2 block text-sm font-medium text-gray-900">
                        投稿履歴を見る
                    </span>
                </a>
            </div>
        </div>
    </div>

    <!-- 最近の投稿 -->
    <div class="mt-8">
        <h2 class="text-lg font-medium text-gray-900 mb-4">最近の投稿</h2>
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <ul role="list" class="divide-y divide-gray-200">
                {% for post in recent_posts %}
                <li>
                    <a href="{% url 'blog:detail' post.id %}" class="block hover:bg-gray-50">
                        <div class="px-4 py-4 sm:px-6">
                            <div class="flex items-center justify-between">
                                <p class="text-sm font-medium text-blue-600 truncate">
                                    {{ post.title }}
                                </p>
                                <div class="ml-2 flex-shrink-0 flex">
                                    <p class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                                       {% if post.status == 'completed' %}bg-green-100 text-green-800
                                       {% elif post.status == 'processing' %}bg-yellow-100 text-yellow-800
                                       {% elif post.status == 'failed' %}bg-red-100 text-red-800
                                       {% else %}bg-gray-100 text-gray-800{% endif %}">
                                        {% if post.status == 'completed' %}完了
                                        {% elif post.status == 'processing' %}処理中
                                        {% elif post.status == 'failed' %}失敗
                                        {% else %}下書き{% endif %}
                                    </p>
                                </div>
                            </div>
                            <div class="mt-2 sm:flex sm:justify-between">
                                <div class="sm:flex">
                                    <p class="flex items-center text-sm text-gray-500">
                                        {{ post.keywords }}
                                    </p>
                                </div>
                                <div class="mt-2 flex items-center text-sm text-gray-500 sm:mt-0">
                                    <p>
                                        {{ post.created_at|date:"Y年m月d日 H:i" }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </a>
                </li>
                {% empty %}
                <li class="px-4 py-4 sm:px-6 text-center text-gray-500">
                    投稿がありません
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 5.3 ブログ新規作成画面

**パス**: `/blog/create/`
**テンプレート**: `templates/blog/create.html`

```html
{% extends 'base.html' %}

{% block title %}ブログ新規作成 - HPBブログ自動化{% endblock %}

{% block content %}
<div class="px-4 py-6 sm:px-0">
    <div class="md:flex md:items-center md:justify-between mb-6">
        <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold text-gray-900">ブログ新規作成</h1>
        </div>
    </div>

    <div class="bg-white shadow sm:rounded-lg">
        <form id="blog-form" enctype="multipart/form-data" class="space-y-6 p-6">
            {% csrf_token %}

            <!-- キーワード -->
            <div>
                <label for="keywords" class="block text-sm font-medium text-gray-700">
                    キーワード <span class="text-red-500">*</span>
                </label>
                <input type="text" name="keywords" id="keywords" required
                       class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="例: カット カラー トリートメント">
                <p class="mt-2 text-sm text-gray-500">
                    記事のメインキーワードを入力してください
                </p>
            </div>

            <!-- トーン -->
            <div>
                <label for="tone" class="block text-sm font-medium text-gray-700">
                    トーン＆マナー <span class="text-red-500">*</span>
                </label>
                <select name="tone" id="tone" required
                        class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm">
                    {% for value, label in tone_choices %}
                    <option value="{{ value }}">{{ label }}</option>
                    {% endfor %}
                </select>
            </div>

            <!-- 画像アップロード -->
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    画像アップロード <span class="text-red-500">*</span> (最大4枚)
                </label>
                <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                    <div class="space-y-1 text-center">
                        <svg class="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        <div class="flex text-sm text-gray-600">
                            <label for="images" class="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500 focus-within:outline-none focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-blue-500">
                                <span>画像を選択</span>
                                <input id="images" name="images" type="file" accept="image/*" multiple required class="sr-only">
                            </label>
                        </div>
                        <p class="text-xs text-gray-500">PNG, JPG, WEBP（最大10MB/枚）</p>
                    </div>
                </div>
                <div id="image-preview" class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4"></div>
            </div>

            <!-- スタイリストID -->
            <div>
                <label for="stylist_id" class="block text-sm font-medium text-gray-700">
                    スタイリストID（T番号）
                </label>
                <input type="text" name="stylist_id" id="stylist_id"
                       class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="例: T000123456">
                <p class="mt-2 text-sm text-gray-500">
                    空欄の場合は「指定なし」で投稿されます
                </p>
            </div>

            <!-- クーポン名 -->
            <div>
                <label for="coupon_name" class="block text-sm font-medium text-gray-700">
                    クーポン名
                </label>
                <input type="text" name="coupon_name" id="coupon_name"
                       class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                       placeholder="例: カット＋カラー">
                <p class="mt-2 text-sm text-gray-500">
                    部分一致で検索されます
                </p>
            </div>

            <!-- 進捗バー（非表示初期状態） -->
            <div id="progress-container" class="hidden">
                <div class="mb-2">
                    <div class="flex justify-between mb-1">
                        <span class="text-sm font-medium text-blue-700">処理中...</span>
                        <span class="text-sm font-medium text-blue-700" id="progress-percent">0%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div id="progress-bar-fill" class="bg-blue-600 h-2.5 rounded-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                </div>
                <p id="progress-message" class="text-sm text-gray-600"></p>
            </div>

            <!-- エラー表示 -->
            <div id="error-container" class="hidden bg-red-50 border border-red-200 rounded-md p-4">
                <div class="flex">
                    <div class="flex-shrink-0">
                        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">エラーが発生しました</h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p id="error-message"></p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ボタン -->
            <div class="flex justify-end space-x-3">
                <a href="{% url 'blog:list' %}"
                   class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    キャンセル
                </a>
                <button type="submit" id="submit-btn"
                        class="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    作成して投稿
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{% static 'js/image-preview.js' %}"></script>
<script src="{% static 'js/websocket.js' %}"></script>
<script>
// フォーム送信処理
document.getElementById('blog-form').addEventListener('submit', async function(e) {
    e.preventDefault();

    const submitBtn = document.getElementById('submit-btn');
    const progressContainer = document.getElementById('progress-container');
    const errorContainer = document.getElementById('error-container');

    // ボタン無効化
    submitBtn.disabled = true;
    submitBtn.textContent = '処理中...';

    // エラー非表示
    errorContainer.classList.add('hidden');

    const formData = new FormData(this);

    try {
        const response = await fetch('/api/blog/create/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        });

        const data = await response.json();

        if (response.ok) {
            // 進捗バー表示
            progressContainer.classList.remove('hidden');
            // WebSocketで進捗を待つ（websocket.jsで実装）
            console.log('Task started:', data.task_id);
        } else {
            // エラー表示
            document.getElementById('error-message').textContent = data.error || 'エラーが発生しました';
            errorContainer.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.textContent = '作成して投稿';
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('error-message').textContent = '送信に失敗しました';
        errorContainer.classList.remove('hidden');
        submitBtn.disabled = false;
        submitBtn.textContent = '作成して投稿';
    }
});
</script>
{% endblock %}
```

---

### 5.4 AI生成中画面

**パス**: `/blog/{id}/generating/`
**テンプレート**: `templates/blog/generating.html`

```html
{% extends "base.html" %}

{% block title %}AI記事生成中 - HPBブログ自動化{% endblock %}

{% block content %}
<div class="max-w-2xl mx-auto px-6 lg:px-8 py-10">
    <!-- Header -->
    <header class="mb-10 text-center">
        <h1 class="text-display text-gray-900 mb-4">AI記事生成中</h1>
        <p class="text-body text-gray-500">3つの記事案を生成しています...</p>
    </header>
    
    <!-- Progress Card -->
    <div class="card">
        <div class="flex flex-col items-center py-8">
            <!-- Spinner -->
            <div class="relative mb-8">
                <div class="w-20 h-20 border-4 border-gray-200 rounded-full"></div>
                <div class="absolute top-0 left-0 w-20 h-20 border-4 border-pink-500 rounded-full border-t-transparent animate-spin"></div>
            </div>
            
            <!-- Progress Text -->
            <div id="progress-container" class="w-full max-w-md">
                <div class="flex justify-between text-caption text-gray-500 mb-2">
                    <span id="progress-message">準備中...</span>
                    <span id="progress-percent">0%</span>
                </div>
                <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div id="progress-bar" class="h-full bg-pink-500 rounded-full transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

**機能**:
- WebSocketでリアルタイム進捗表示
- 生成完了後、記事選択画面へ自動リダイレクト
- ポーリングによるフォールバック対応

---

### 5.5 記事選択画面

**パス**: `/blog/{id}/select/`
**テンプレート**: `templates/blog/select_article.html`

```html
{% extends "base.html" %}

{% block title %}記事を選択 - HPBブログ自動化{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto px-6 lg:px-8 py-10">
    <!-- Header -->
    <header class="mb-10">
        <h1 class="text-display text-gray-900 mb-2">記事を選択</h1>
        <p class="text-body text-gray-500">AIが生成した3つの記事案から選択してください</p>
    </header>
    
    <!-- Article Variations -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {% for variation in variations %}
        <div class="card hover:border-pink-300 cursor-pointer article-card" 
             data-variation-id="{{ variation.id }}">
            <!-- Header -->
            <span class="text-caption font-medium text-pink-500">案 {{ variation.id }}</span>
            
            <!-- Title -->
            <h3 class="text-title text-gray-900 mb-3">{{ variation.title }}</h3>
            
            <!-- Content Preview -->
            <div class="text-body text-gray-600 leading-relaxed" style="max-height: 300px; overflow-y: auto;">
                {{ variation.content|linebreaksbr }}
            </div>
        </div>
        {% endfor %}
    </div>
    
    <!-- Action Button -->
    <form method="post" action="{% url 'blog:post_select_confirm' pk=post.pk %}">
        {% csrf_token %}
        <input type="hidden" name="variation_id" id="selected-variation-id" value="">
        <button type="submit" class="btn btn-primary" id="confirm-btn" disabled>
            この記事を使う
        </button>
    </form>
</div>
{% endblock %}
```

**機能**:
- 3つの記事案をカード形式で表示
- クリックで選択状態をトグル
- 全文プレビューモーダル
- 選択した記事を確定してready状態へ遷移

**ワイヤーフレーム**:
```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│    記事を選択                                                     │
│    AIが生成した3つの記事案から選択してください                        │
│                                                                  │
│    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐│
│    │ 案 1             │ │ 案 2             │ │ 案 3             ││
│    │                  │ │                  │ │                  ││
│    │ タイトル案1       │ │ タイトル案2       │ │ タイトル案3       ││
│    │                  │ │                  │ │                  ││
│    │ 本文プレビュー...  │ │ 本文プレビュー...  │ │ 本文プレビュー...  ││
│    │                  │ │                  │ │                  ││
│    │ [全文を見る]      │ │ [全文を見る]      │ │ [全文を見る]      ││
│    └──────────────────┘ └──────────────────┘ └──────────────────┘│
│                                                                  │
│    案1を選択中              [やり直す] [この記事を使う]             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. JavaScriptモジュール

### 6.1 WebSocket処理

```javascript
// static/js/websocket.js
(function() {
    // WebSocket接続
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/blog/progress/`;
    let socket = null;

    function connectWebSocket() {
        socket = new WebSocket(wsUrl);

        socket.onopen = function(e) {
            console.log('WebSocket connection established');
        };

        socket.onmessage = function(event) {
            const data = JSON.parse(event.data);

            if (data.type === 'task_progress') {
                updateProgress(data);

                // 完了時の処理
                if (data.status === 'completed') {
                    setTimeout(() => {
                        window.location.href = '/blog/';
                    }, 2000);
                }
            } else if (data.type === 'task_error') {
                showError(data);
            }
        };

        socket.onerror = function(error) {
            console.error('WebSocket error:', error);
        };

        socket.onclose = function(event) {
            console.log('WebSocket connection closed');
            // 再接続
            setTimeout(connectWebSocket, 3000);
        };
    }

    function updateProgress(data) {
        const progressBar = document.getElementById('progress-bar-fill');
        const progressPercent = document.getElementById('progress-percent');
        const progressMessage = document.getElementById('progress-message');

        if (progressBar) {
            progressBar.style.width = data.progress + '%';
        }
        if (progressPercent) {
            progressPercent.textContent = data.progress + '%';
        }
        if (progressMessage) {
            progressMessage.textContent = data.message;
        }
    }

    function showError(data) {
        const errorContainer = document.getElementById('error-container');
        const errorMessage = document.getElementById('error-message');
        const progressContainer = document.getElementById('progress-container');

        if (errorContainer) {
            errorContainer.classList.remove('hidden');
        }
        if (errorMessage) {
            errorMessage.textContent = data.message || data.error;
        }
        if (progressContainer) {
            progressContainer.classList.add('hidden');
        }
    }

    // ページロード時に接続
    if (window.location.pathname === '/blog/create/') {
        connectWebSocket();
    }
})();
```

### 6.2 画像プレビュー

```javascript
// static/js/image-preview.js
document.getElementById('images').addEventListener('change', function(e) {
    const files = Array.from(e.target.files);
    const preview = document.getElementById('image-preview');
    preview.innerHTML = '';

    if (files.length > 4) {
        alert('画像は最大4枚までです');
        e.target.value = '';
        return;
    }

    files.forEach((file, index) => {
        if (file.size > 10 * 1024 * 1024) {
            alert(`${file.name} は10MBを超えています`);
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const div = document.createElement('div');
            div.className = 'relative';
            div.innerHTML = `
                <img src="${e.target.result}" class="h-32 w-full object-cover rounded-lg">
                <div class="absolute top-2 right-2 bg-white rounded-full px-2 py-1 text-xs font-semibold">
                    ${index + 1}
                </div>
            `;
            preview.appendChild(div);
        };
        reader.readAsDataURL(file);
    });
});
```

---

## 7. レスポンシブ対応

### 7.1 ブレークポイント

```css
/* Tailwind CSS デフォルトブレークポイント */
sm: 640px   /* タブレット縦 */
md: 768px   /* タブレット横 */
lg: 1024px  /* PC小 */
xl: 1280px  /* PC大 */
2xl: 1536px /* PC特大 */
```

### 7.2 モバイルファーストデザイン

- 基本はモバイル向けのスタイル
- `sm:`、`md:`プレフィックスで大画面対応
- タッチ操作を考慮したボタンサイズ（最小44px×44px）

---

## 8. アクセシビリティ

### 8.1 WCAG 2.1 準拠

- **カラーコントラスト**: 4.5:1以上
- **キーボード操作**: Tab移動可能
- **スクリーンリーダー**: aria-label, role属性
- **フォーカス表示**: focus:ring-*で明示

### 8.2 実装例

```html
<!-- ボタン -->
<button type="button"
        aria-label="ブログを作成"
        class="focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
    作成
</button>

<!-- フォーム -->
<label for="title" class="sr-only">タイトル</label>
<input id="title" type="text" aria-required="true">
```

---

## 9. まとめ

このフロントエンド設計により：
- **統一感**: Tailwind CSSによる一貫したデザイン
- **レスポンシブ**: あらゆる画面サイズで最適表示
- **リアルタイム**: WebSocketで即座にフィードバック
- **アクセシブル**: WCAG準拠で誰でも使える
- **保守性**: コンポーネント化で再利用容易

これで全ドキュメントが完成し、実装開始の準備が整いました！

---

**作成日**: 2025年1月
**最終更新**: 2025年11月
**ステータス**: AI3案生成対応（generating/select画面追加）
