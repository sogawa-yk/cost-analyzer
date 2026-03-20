# API Contract: /query エンドポイント拡張

**Feature**: 006-nl-chat-ui | **Date**: 2026-03-20

## 変更概要

既存の `POST /query` エンドポイントのレスポンスに `conversational_text` フィールドを追加する。既存フィールドはすべて後方互換で維持する。

## リクエスト（変更なし）

```
POST /query
Content-Type: application/json
```

```json
{
  "query": "先月のサービス別コストを教えて",
  "format": "json",
  "lang": "auto"
}
```

## レスポンス拡張

### Breakdown レスポンス

```json
{
  "type": "breakdown",
  "conversational_text": "先月のコスト内訳です。Compute が全体の45.2%を占め、最もコストが高いサービスです。",
  "period": { "start": "2026-02-01", "end": "2026-03-01" },
  "currency": "USD",
  "items": [
    { "service": "COMPUTE", "amount": 1000.00, "percentage": 45.2, "rank": 1 },
    { "service": "STORAGE", "amount": 800.00, "percentage": 36.1, "rank": 2 }
  ],
  "total": 2200.00
}
```

### Comparison レスポンス

```json
{
  "type": "comparison",
  "conversational_text": "先月と比べて合計コストが5.0%増加しています。Computeの増加が最も大きく、前月比+$200です。",
  "current_period": { "start": "2026-02-01", "end": "2026-03-01" },
  "previous_period": { "start": "2026-01-01", "end": "2026-02-01" },
  "currency": "USD",
  "items": [ ... ],
  "previous_period_total": 2000.00,
  "current_period_total": 2100.00,
  "total_change": 100.00,
  "total_change_percent": 5.0,
  "summary": "合計コストが $100 (+5.0%) 増加しました。..."
}
```

### Clarification レスポンス（変更なし）

```json
{
  "type": "clarification",
  "message": "どの期間のコストを知りたいですか？",
  "suggestions": []
}
```

### Error レスポンス（変更なし）

```json
{
  "error": "parse_error",
  "message": "クエリを解析できませんでした",
  "guidance": "コストに関する質問を入力してください",
  "suggestions": ["先月のコストを教えて", "今月と先月を比較して"]
}
```

## 新規フィールド仕様

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| conversational_text | string | Yes | LLM生成の対話文。breakdown/comparison レスポンスにのみ含まれる。LLM呼び出し失敗時は null（テーブルデータのみ表示にフォールバック） |

## 後方互換性

- 既存のフィールドはすべて維持。型・構造に変更なし
- `conversational_text` は新規追加フィールドのため、既存クライアント（CLI、A2A）は無視可能
- `summary` フィールド（comparison レスポンス）は維持。`conversational_text` はより自然な対話文で、`summary` はデータ駆動のトレンドサマリー
