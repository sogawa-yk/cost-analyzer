# Quickstart: エージェント間連携（Agent Interoperability）

**Date**: 2026-03-18
**Feature**: 003-agent-interop

## 前提条件

- Python 3.13+
- OCI 認証設定済み（`~/.oci/config` または Instance Principal）
- cost-analyzer がインストール済み

## セットアップ

```bash
# 依存関係の追加インストール
pip install "a2a-sdk[http-server]"

# サーバー起動（既存の serve コマンドで A2A も同時に起動）
cost-analyzer serve --host 0.0.0.0 --port 8080
```

## Agent Card の確認

```bash
curl http://localhost:8080/.well-known/agent-card.json | python -m json.tool
```

## 使い方: 自然言語クエリ

```bash
curl -X POST http://localhost:8080/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "先月のサービス別コストを教えて"}],
        "messageId": "msg-1"
      }
    }
  }'
```

## 使い方: 構造化パラメータ

```bash
# コスト内訳
curl -X POST http://localhost:8080/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{
          "kind": "data",
          "data": {
            "skill": "get_cost_breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "lang": "ja"
          }
        }],
        "messageId": "msg-2"
      }
    }
  }'
```

## 使い方: Python クライアント

```python
import httpx
from a2a.client import A2AClient

async def main():
    async with httpx.AsyncClient() as http:
        # Agent Card 取得
        client = await A2AClient.get_client_from_agent_card_url(
            http, "http://localhost:8080/.well-known/agent-card.json"
        )

        # 自然言語クエリ送信
        response = await client.send_message(
            SendMessageRequest(
                id="1",
                params=MessageSendParams(
                    message={
                        "role": "user",
                        "parts": [{"kind": "text", "text": "先月のコスト"}],
                        "messageId": "msg-1",
                    }
                ),
            )
        )
        print(response.model_dump_json(indent=2))
```

## 既存機能との共存確認

```bash
# Web UI — 従来通りブラウザでアクセス
open http://localhost:8080/

# HTTP API — 従来通り動作
curl -X POST http://localhost:8080/query \
  -H "Content-Type: application/json" \
  -d '{"query": "先月のコスト", "format": "json"}'

# A2A Agent Card — 新規追加
curl http://localhost:8080/.well-known/agent-card.json

# A2A JSON-RPC — 新規追加
curl -X POST http://localhost:8080/a2a -H "Content-Type: application/json" -d '...'
```
