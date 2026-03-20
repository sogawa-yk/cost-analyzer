# Data Model: コンパートメント別集計（group_by）対応

**Date**: 2026-03-20

## エンティティ変更

### CostQuery（変更）

| フィールド | 型 | デフォルト | 変更種別 | 説明 |
|-----------|-----|----------|---------|------|
| query_type | QueryType | — | 既存 | クエリ種別 |
| start_date | date | — | 既存 | 開始日 |
| end_date | date | — | 既存 | 終了日 |
| comparison_start_date | date \| None | None | 既存 | 比較開始日 |
| comparison_end_date | date \| None | None | 既存 | 比較終了日 |
| service_filter | str \| None | None | 既存 | サービス絞り込み |
| compartment_filter | str \| None | None | 既存 | コンパートメント絞り込み |
| **group_by** | **str** | **"service"** | **新規** | **集計軸（"service" or "compartment"）** |
| needs_clarification | bool | False | 既存 | 要確認フラグ |
| clarification_message | str \| None | None | 既存 | 確認メッセージ |
| detected_language | str | "ja" | 既存 | 検出言語 |

**バリデーション**: `group_by` は `["service", "compartment"]` のいずれか。不正値の場合は `"service"` にフォールバック。

### ServiceCost（変更）

| フィールド | 型 | 変更種別 | 説明 |
|-----------|-----|---------|------|
| service | str | 既存（エイリアス化） | 後方互換用。`group_key` を返す |
| **group_key** | **str** | **新規** | **集計キー（サービス名 or コンパートメント名）** |
| amount | Decimal | 既存 | 金額 |
| percentage | Decimal | 既存 | 割合 |
| rank | int | 既存 | 順位 |

### ServiceDelta（変更）

| フィールド | 型 | 変更種別 | 説明 |
|-----------|-----|---------|------|
| service | str | 既存（エイリアス化） | 後方互換用。`group_key` を返す |
| **group_key** | **str** | **新規** | **集計キー（サービス名 or コンパートメント名）** |
| current_amount | Decimal | 既存 | 当期金額 |
| previous_amount | Decimal | 既存 | 前期金額 |
| absolute_change | Decimal | 既存 | 差分 |
| percent_change | Decimal \| None | 既存 | 変化率 |

### CostLineItem（変更なし）

既に `compartment_name` / `compartment_path` フィールドが存在。変更不要。

## OCI API group_by マッピング

| group_by 値 | OCI API group_by パラメータ | 集計キー取得元 |
|------------|---------------------------|--------------|
| `"service"` | `["service", "currency"]` | `CostLineItem.service` |
| `"compartment"` | `["compartmentName", "currency"]` | `CostLineItem.compartment_name`（同名重複時は `compartment_path`） |

## API レスポンス変更

### /query 内訳レスポンス（変更）

```json
{
  "type": "breakdown",
  "group_by": "compartment",
  "items": [
    {
      "group_key": "production",
      "amount": 1234.56,
      "percentage": 45.2,
      "rank": 1
    }
  ]
}
```

### /query 比較レスポンス（変更）

```json
{
  "type": "comparison",
  "group_by": "compartment",
  "items": [
    {
      "group_key": "production",
      "current_amount": 1234.56,
      "previous_amount": 1100.00,
      "absolute_change": 134.56,
      "percent_change": 12.23
    }
  ]
}
```
