# API コントラクト: cost-analyzer HTTP インターフェース

ベース URL: `http://{host}:{port}`

---

## POST /query

自然言語コストクエリを送信します。

### リクエスト

```json
{
  "query": "先月のサービス別コストを教えて",
  "format": "json",
  "lang": "auto"
}
```

| フィールド | 型 | 必須 | デフォルト | 説明 |
|---|---|---|---|---|
| `query` | `string` | はい | — | 自然言語コストクエリ |
| `format` | `string` | いいえ | `"json"` | レスポンスフォーマット: `"json"`, `"text"` |
| `lang` | `string` | いいえ | `"auto"` | 言語の強制: `"ja"`, `"en"`, `"auto"` |

### レスポンス — 内訳 (200 OK)

```json
{
  "type": "breakdown",
  "period": {
    "start": "2026-02-01",
    "end": "2026-02-28"
  },
  "currency": "USD",
  "items": [
    {
      "service": "Compute",
      "amount": 1234.56,
      "percentage": 45.2,
      "rank": 1
    }
  ],
  "total": 2733.14
}
```

### レスポンス — 比較 (200 OK)

```json
{
  "type": "comparison",
  "current_period": {
    "start": "2026-02-01",
    "end": "2026-02-28"
  },
  "previous_period": {
    "start": "2026-01-01",
    "end": "2026-01-31"
  },
  "currency": "USD",
  "items": [
    {
      "service": "Compute",
      "current_amount": 1234.56,
      "previous_amount": 1100.00,
      "absolute_change": 134.56,
      "percent_change": 12.2
    }
  ],
  "total_change": 233.14,
  "total_change_percent": 9.3,
  "summary": "合計コストが $233.14 (9.3%) 増加しました。Compute の増加額が最大です。"
}
```

### レスポンス — 確認が必要 (200 OK)

```json
{
  "type": "clarification",
  "message": "「最近」はどの期間を指しますか？",
  "suggestions": [
    "先月 (2026年2月)",
    "過去30日間",
    "今月これまで"
  ]
}
```

### エラーレスポンス

**400 Bad Request** — クエリがパースできない
```json
{
  "error": "parse_error",
  "message": "クエリを理解できませんでした。",
  "example_queries": [
    "先月のサービス別コストを教えて",
    "Show costs for February 2026"
  ]
}
```

**401 Unauthorized** — OCI 認証情報が無効
```json
{
  "error": "auth_error",
  "message": "OCI 認証に失敗しました。",
  "guidance": "OCI 認証情報の設定を確認してください。"
}
```

**502 Bad Gateway** — OCI API が利用不可
```json
{
  "error": "api_error",
  "message": "OCI コスト管理 API が一時的に利用できません。",
  "guidance": "数分後に再試行してください。"
}
```

---

## GET /health

Kubernetes プローブ用のヘルスチェックエンドポイント。

### レスポンス (200 OK)

```json
{
  "status": "healthy",
  "checks": {
    "oci_usage_api": "ok",
    "oci_genai": "ok"
  }
}
```

### レスポンス (503 Service Unavailable)

```json
{
  "status": "unhealthy",
  "checks": {
    "oci_usage_api": "error: authentication failed",
    "oci_genai": "ok"
  }
}
```
