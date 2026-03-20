# Data Model: NL チャット UI

**Feature**: 006-nl-chat-ui | **Date**: 2026-03-20

## フロントエンド状態モデル（Alpine.js ストア）

### ChatMessage

チャット画面に表示される個々のメッセージを表現する。

| Field | Type | Description |
|-------|------|-------------|
| id | string | 一意識別子（タイムスタンプベース） |
| role | "user" \| "assistant" | メッセージの送信者 |
| type | "text" \| "breakdown" \| "comparison" \| "clarification" \| "error" \| "welcome" | メッセージの種別 |
| text | string \| null | テキストコンテンツ（対話文、エラーメッセージ、ユーザー入力） |
| data | object \| null | 構造化データ（breakdown/comparison のレスポンス JSON） |
| timestamp | number | メッセージ作成時刻（Date.now()） |

**バリデーションルール**:
- `role === "user"` の場合、`type` は常に `"text"`、`data` は常に `null`
- `role === "assistant"` の場合、`type` に応じて `text` と `data` の組み合わせが決まる
- `type === "welcome"` のメッセージは会話内に最大1つ（先頭のみ）

**ライフサイクル**:
- 生成: ユーザー送信時（user）またはAPI応答受信時（assistant）
- 保持: ブラウザメモリ内の配列に追加のみ（削除は会話クリア時のみ）
- 削除: 会話クリア操作またはページリロード時に全削除

### AppStore（Alpine.js ストア拡張）

| Field | Type | Description | 変更 |
|-------|------|-------------|------|
| messages | ChatMessage[] | 全メッセージの時系列配列 | 新規 |
| loading | boolean | 処理中フラグ | 既存維持 |
| backendHealthy | boolean | バックエンド接続状態 | 既存維持 |
| queryText | string | 入力テキスト | 既存維持 |
| result | - | 廃止 | 削除 |
| clarification | - | 廃止 | 削除 |
| error | - | 廃止 | 削除 |

## バックエンドモデル（Python / Pydantic）

### ConversationalResponse（新規）

応答文生成LLMの出力を表現する。

| Field | Type | Description |
|-------|------|-------------|
| text | str | LLM生成の対話文（200文字以内目標） |
| language | str | 生成言語（"ja" \| "en"） |

**バリデーションルール**:
- `text` は空文字列不可
- `language` は "ja" または "en" のみ

### QueryResponse 拡張（既存モデルへのフィールド追加）

`/query` エンドポイントのレスポンスに `conversational_text` フィールドを追加する。

| Field | Type | Description | 変更 |
|-------|------|-------------|------|
| type | str | "breakdown" \| "comparison" \| "clarification" | 既存 |
| conversational_text | str \| null | LLM生成の対話文 | 新規 |
| ... | ... | 既存フィールドはすべて維持 | 既存 |

**状態遷移**: なし（ステートレス — リクエストごとに独立処理）

## エンティティ関係

```text
ユーザー入力 (queryText)
    │
    ▼
[POST /query]
    │
    ├─→ parse_query() ─→ CostQuery (既存)
    │
    ├─→ fetch_breakdown() / fetch_comparison() ─→ コスト結果データ (既存)
    │
    └─→ generate_conversational_response() ─→ ConversationalResponse (新規)
            │
            ▼
    QueryResponse { type, data, conversational_text }
            │
            ▼
    ChatMessage { role: "assistant", type, text: conversational_text, data }
```
