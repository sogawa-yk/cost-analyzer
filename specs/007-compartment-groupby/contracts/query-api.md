# Contract: /query API エンドポイント

**Date**: 2026-03-20

## POST /query

### リクエスト（変更なし）

```json
{
  "message": "コンパートメント別のコストを教えて"
}
```

### レスポンス（変更あり）

#### 内訳レスポンス

**追加フィールド**: `group_by` — 集計軸を示す文字列（`"service"` or `"compartment"`）
**変更フィールド**: items 配列内に `group_key` フィールド追加

```json
{
  "type": "breakdown",
  "group_by": "compartment",
  "period": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-20"
  },
  "total": 5000.00,
  "currency": "JPY",
  "items": [
    {
      "group_key": "production",
      "amount": 2500.00,
      "percentage": 50.0,
      "rank": 1
    },
    {
      "group_key": "development",
      "amount": 1500.00,
      "percentage": 30.0,
      "rank": 2
    }
  ]
}
```

#### 比較レスポンス

```json
{
  "type": "comparison",
  "group_by": "compartment",
  "items": [
    {
      "group_key": "production",
      "current_amount": 2500.00,
      "previous_amount": 2200.00,
      "absolute_change": 300.00,
      "percent_change": 13.64
    }
  ]
}
```

#### 後方互換性

`group_by` が `"service"` の場合（デフォルト）、レスポンス構造は従来通り。`group_key` フィールドが追加されるが、`service` フィールドも引き続き存在する（同じ値）。

```json
{
  "type": "breakdown",
  "group_by": "service",
  "items": [
    {
      "group_key": "COMPUTE",
      "service": "COMPUTE",
      "amount": 1234.56,
      "percentage": 45.2,
      "rank": 1
    }
  ]
}
```
