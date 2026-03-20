# Data Model: NL クエリ品質改善

**Date**: 2026-03-20

## 既存モデルへの変更

本機能は既存モデルの変更を伴わない。以下は参照用の既存モデル構造。

### CostQuery（変更なし）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| query_type | QueryType | Yes | "breakdown" or "comparison" |
| start_date | date | Yes | 期間開始日（含む） |
| end_date | date | Yes | 期間終了日（含まない） |
| comparison_start_date | date | No | 比較対象の前期間開始日 |
| comparison_end_date | date | No | 比較対象の前期間終了日 |
| service_filter | str | No | OCI サービス名フィルタ |
| compartment_filter | str | No | コンパートメント名フィルタ |
| needs_clarification | bool | No | 確認質問が必要かどうか |
| clarification_message | str | No | 確認質問テキスト |
| detected_language | str | Yes | "ja" or "en" |

### バリデーションルール（変更なし）

1. `start_date < end_date`
2. COMPARISON 時: `comparison_start_date` と `comparison_end_date` の両方が必須
3. COMPARISON 時: `comparison_start_date < comparison_end_date`
4. `needs_clarification=true` 時: `clarification_message` が必須
5. `detected_language` は "ja" or "en"

### ErrorResponse（変更なし）

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| error_type | ErrorType | Yes | auth_error, api_error, parse_error, no_data |
| message | str | Yes | ユーザー向けメッセージ |
| guidance | str | Yes | ガイダンスメッセージ |
| example_queries | list[str] | No | クエリ例 |

## 変更箇所

変更はデータモデルではなく、パーサーロジック（`parser.py`）に集中する:

1. **システムプロンプト**: 比較クエリの JSON 出力例追加、サービスフィルタ抽出例追加
2. **ValidationError ハンドリング**: `CostQuery` 構築失敗時のフォールバック処理追加
3. **比較日付の自動推定**: `query_type=comparison` で比較日付が省略された場合の推定ロジック
