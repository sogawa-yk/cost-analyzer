# データモデル: 自然言語 OCI コストクエリ

**日付**: 2026-03-17
**ブランチ**: `001-nl-cost-query`

---

## エンティティ

### CostQuery（コストクエリ）

自然言語入力からパースされたユーザーリクエストを表します。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `query_type` | `QueryType` 列挙型 | はい | `BREAKDOWN` または `COMPARISON` |
| `start_date` | `date` | はい | クエリ期間の開始日（含む） |
| `end_date` | `date` | はい | クエリ期間の終了日（含まない） |
| `comparison_start_date` | `date` | いいえ | 比較期間の開始日（`COMPARISON` の場合必須） |
| `comparison_end_date` | `date` | いいえ | 比較期間の終了日（`COMPARISON` の場合必須） |
| `service_filter` | `str` | いいえ | フィルタする OCI サービス名（例: `"COMPUTE"`） |
| `compartment_filter` | `str` | いいえ | OCI コンパートメント名または OCID |
| `needs_clarification` | `bool` | はい | クエリが曖昧な場合 `True` |
| `clarification_message` | `str` | いいえ | ユーザーへの確認質問（`needs_clarification=True` の場合） |
| `detected_language` | `str` | はい | `"ja"` または `"en"` |

**バリデーションルール**:
- `start_date < end_date`
- `query_type == COMPARISON` の場合: `comparison_start_date` と `comparison_end_date` の両方が設定されていること
- `needs_clarification == True` の場合: `clarification_message` が空でないこと
- `detected_language` は `"ja"` または `"en"` であること

---

### CostLineItem（コスト明細）

OCI Usage API から返される単一のコストエントリ。`oci.usage_api.models.UsageSummary` に直接マッピングされます。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `service` | `str` | はい | OCI サービス名（例: `"COMPUTE"`, `"OBJECT_STORAGE"`） |
| `amount` | `Decimal` | はい | 期間のコスト金額 |
| `currency` | `str` | はい | 通貨コード（例: `"USD"`, `"JPY"`） |
| `compartment_name` | `str` | いいえ | コンパートメント名 |
| `compartment_path` | `str` | いいえ | コンパートメント階層のフルパス |
| `time_usage_started` | `datetime` | はい | 期間の開始 |
| `time_usage_ended` | `datetime` | はい | 期間の終了 |

**バリデーションルール**:
- `amount >= 0`
- `currency` は有効な ISO 4217 コードであること
- `time_usage_started < time_usage_ended`

---

### CostBreakdown（コスト内訳）

`CostLineItem` のコレクションから導出された、サービス別に集約されたコストデータ。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `period_start` | `date` | はい | 集約期間の開始 |
| `period_end` | `date` | はい | 集約期間の終了 |
| `currency` | `str` | はい | 通貨コード |
| `items` | `list[ServiceCost]` | はい | サービス別コスト、金額降順ソート |
| `total` | `Decimal` | はい | 全サービスコストの合計 |

---

### ServiceCost（サービスコスト）

コスト内訳テーブルの単一行。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `service` | `str` | はい | OCI サービス名 |
| `amount` | `Decimal` | はい | 期間中のこのサービスの合計コスト |
| `percentage` | `Decimal` | はい | 合計コストに対する割合 (0-100) |
| `rank` | `int` | はい | コスト順の順位（1 = 最高） |

**バリデーションルール**:
- `0 <= percentage <= 100`
- `rank >= 1`

---

### CostComparison（コスト比較）

傾向比較のための2つの `CostBreakdown` オブジェクトのペア分析。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `current_period` | `CostBreakdown` | はい | 主要/当期間 |
| `previous_period` | `CostBreakdown` | はい | 比較/前期間 |
| `items` | `list[ServiceDelta]` | はい | サービス別差分、絶対変化額降順ソート |
| `total_change` | `Decimal` | はい | コスト合計の絶対変化額 |
| `total_change_percent` | `Decimal` | はい | コスト合計の変化率 |

---

### ServiceDelta（サービス差分）

コスト比較テーブルの単一行。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `service` | `str` | はい | OCI サービス名 |
| `current_amount` | `Decimal` | はい | 当期間のコスト |
| `previous_amount` | `Decimal` | はい | 前期間のコスト |
| `absolute_change` | `Decimal` | はい | `current_amount - previous_amount` |
| `percent_change` | `Decimal` | いいえ | 変化率（`previous_amount == 0` の場合 None） |

---

### TrendSummary（傾向サマリー）

`CostComparison` から導出された自然言語ナラティブ。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `language` | `str` | はい | `"ja"` または `"en"` |
| `overall_direction` | `str` | はい | `"increase"`, `"decrease"`, または `"stable"` |
| `total_change_text` | `str` | はい | 例: "合計コストが $150 (12%) 増加しました" |
| `top_increases` | `list[str]` | はい | コスト増加が最大のトップ3サービス |
| `notable_decreases` | `list[str]` | はい | 顕著に減少したサービス |
| `summary_text` | `str` | はい | 完全なナラティブ段落 |

---

### ErrorResponse（エラーレスポンス）

ユーザーに返される構造化エラー。

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `error_type` | `ErrorType` 列挙型 | はい | `AUTH_ERROR`, `API_ERROR`, `PARSE_ERROR`, `NO_DATA` |
| `message` | `str` | はい | ユーザーフレンドリーなエラーメッセージ |
| `guidance` | `str` | はい | ユーザーへの実行可能な次のステップ |
| `example_queries` | `list[str]` | いいえ | クエリ例（`PARSE_ERROR` の場合） |

---

## 列挙型

### QueryType
- `BREAKDOWN` — 単一期間のサービス別コスト内訳
- `COMPARISON` — 2期間のコスト比較と傾向分析

### ErrorType
- `AUTH_ERROR` — OCI 認証情報が無効または期限切れ
- `API_ERROR` — OCI API 呼び出しが失敗
- `PARSE_ERROR` — 自然言語クエリが理解できない
- `NO_DATA` — 指定された期間/スコープにコストデータなし

---

## エンティティ関係

```
ユーザー入力（自然言語）
    │
    ▼
CostQuery ─────────────────────────┐
    │                               │
    ▼ (query_type=BREAKDOWN)        ▼ (query_type=COMPARISON)
CostLineItem[]                  CostLineItem[] (×2 期間)
    │                               │
    ▼                               ▼
CostBreakdown                   CostComparison
    │                               │
    ▼                               ▼
ServiceCost[]                   ServiceDelta[] + TrendSummary
```

## 状態遷移

`CostQuery` はミュータブルな状態を持ちません — ユーザー入力から一度作成され、コストエンジンによって消費されます。処理フローは以下の通りです:

1. **パース** → `CostQuery`（または `PARSE_ERROR` の `ErrorResponse`）
2. **バリデーション** → `needs_clarification` を確認; true の場合、ユーザーに確認を返す
3. **取得** → OCI API 呼び出し → `CostLineItem[]`（または `AUTH_ERROR`/`API_ERROR` の `ErrorResponse`）
4. **集約** → `CostBreakdown` または `CostComparison`（または `NO_DATA` の `ErrorResponse`）
5. **要約** → `TrendSummary`（比較の場合のみ）
6. **フォーマット** → Rich テーブル出力をユーザーに
