# コードスタイルと規約

## 命名規則
- クラス名: PascalCase (例: `BlogPost`, `GeminiClient`)
- 関数・変数: snake_case (例: `get_user_posts`, `user_id`)
- 定数: UPPER_SNAKE_CASE (例: `STATUS_CHOICES`)

## ファイル構成
- モデル: `models.py`
- ビュー: `views.py` (ViewSetベース)
- URL設定: `urls.py` (Routerベース)
- シリアライザー: `serializers.py`
- Celeryタスク: `tasks.py`

## docstring形式
- Google形式のdocstring（Args, Returns, Raises）

## 型ヒント
- 積極的に使用（from typing import Dict, List, Optional等）

## ロギング
- 各モジュールで`logger = logging.getLogger(__name__)`を定義
