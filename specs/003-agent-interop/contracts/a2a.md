# A2A Contract: Cost Analyzer Agent

**Date**: 2026-03-18
**Protocol**: A2A (Agent-to-Agent Protocol) v0.3.0
**Transport**: HTTPS + JSON-RPC 2.0

## Endpoints

### Agent Card Discovery

```
GET /.well-known/agent-card.json
```

**Response** (200):
```json
{
  "protocolVersion": "0.3.0",
  "name": "Cost Analyzer Agent",
  "description": "OCI cost analysis agent that provides cost breakdown, comparison, and resource discovery capabilities via natural language or structured parameters.",
  "url": "http://{host}:{port}/a2a",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "defaultInputModes": ["text", "data"],
  "defaultOutputModes": ["text", "data"],
  "skills": [
    {
      "id": "analyze_cost",
      "name": "Cost Analysis (Natural Language)",
      "description": "Analyze OCI costs using natural language queries in Japanese or English. Automatically detects whether to show a breakdown or comparison.",
      "tags": ["oci", "cost", "natural-language"],
      "examples": [
        "先月のサービス別コストを教えて",
        "Show me last month's cost breakdown",
        "先月と今月のコストを比較して"
      ],
      "inputModes": ["text"],
      "outputModes": ["text", "data"]
    },
    {
      "id": "get_cost_breakdown",
      "name": "Cost Breakdown",
      "description": "Get cost breakdown by service for a specified period using structured parameters. No LLM parsing required.",
      "tags": ["oci", "cost", "breakdown", "structured"],
      "examples": [
        "Get cost breakdown for February 2026"
      ],
      "inputModes": ["data"],
      "outputModes": ["text", "data"]
    },
    {
      "id": "compare_costs",
      "name": "Cost Comparison",
      "description": "Compare costs between two periods using structured parameters. Returns absolute and percentage changes per service.",
      "tags": ["oci", "cost", "comparison", "structured"],
      "examples": [
        "Compare January and February 2026 costs"
      ],
      "inputModes": ["data"],
      "outputModes": ["text", "data"]
    },
    {
      "id": "list_services",
      "name": "List Available Services",
      "description": "List all OCI services with cost data available in the tenancy.",
      "tags": ["oci", "services", "discovery"],
      "examples": [
        "What services are available?"
      ],
      "inputModes": ["text", "data"],
      "outputModes": ["data"]
    },
    {
      "id": "list_compartments",
      "name": "List Available Compartments",
      "description": "List all OCI compartments available in the tenancy.",
      "tags": ["oci", "compartments", "discovery"],
      "examples": [
        "List compartments"
      ],
      "inputModes": ["text", "data"],
      "outputModes": ["data"]
    },
    {
      "id": "health_check",
      "name": "Health Check",
      "description": "Check connectivity to OCI Usage API and GenAI service.",
      "tags": ["health", "status"],
      "examples": [
        "Check system health"
      ],
      "inputModes": ["text", "data"],
      "outputModes": ["data"]
    }
  ]
}
```

### JSON-RPC Endpoint

```
POST /a2a
Content-Type: application/json
```

#### message/send — 自然言語クエリ（analyze_cost スキル）

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {"kind": "text", "text": "先月のサービス別コストを教えて"}
      ],
      "messageId": "msg-001"
    }
  }
}
```

**Response** (成功 — breakdown):
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "id": "task-uuid",
    "contextId": "ctx-uuid",
    "status": {
      "state": "completed",
      "timestamp": "2026-03-18T10:00:00Z"
    },
    "artifacts": [
      {
        "artifactId": "result-001",
        "parts": [
          {
            "kind": "data",
            "data": {
              "type": "breakdown",
              "data": {
                "period_start": "2026-02-01",
                "period_end": "2026-02-28",
                "currency": "USD",
                "items": [
                  {"service": "Compute", "amount": 1234.56, "percentage": 45.2, "rank": 1},
                  {"service": "Object Storage", "amount": 567.89, "percentage": 20.8, "rank": 2}
                ],
                "total": 2733.14
              },
              "summary": "2026年2月のコスト内訳: 合計 $2,733.14。最大は Compute ($1,234.56, 45.2%)"
            }
          }
        ]
      }
    ],
    "kind": "task"
  }
}
```

#### message/send — 構造化パラメータ（get_cost_breakdown スキル）

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-002",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "data",
          "data": {
            "skill": "get_cost_breakdown",
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "service_filter": "Compute",
            "lang": "en"
          }
        }
      ],
      "messageId": "msg-002"
    }
  }
}
```

#### message/send — 構造化パラメータ（compare_costs スキル）

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-003",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "kind": "data",
          "data": {
            "skill": "compare_costs",
            "start_date": "2026-02-01",
            "end_date": "2026-02-28",
            "comparison_start_date": "2026-01-01",
            "comparison_end_date": "2026-01-31",
            "lang": "ja"
          }
        }
      ],
      "messageId": "msg-003"
    }
  }
}
```

#### message/send — リスト系スキル

**Request** (list_services):
```json
{
  "jsonrpc": "2.0",
  "id": "req-004",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {"kind": "data", "data": {"skill": "list_services"}}
      ],
      "messageId": "msg-004"
    }
  }
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-004",
  "result": {
    "id": "task-uuid",
    "status": {"state": "completed"},
    "artifacts": [
      {
        "artifactId": "result-004",
        "parts": [
          {
            "kind": "data",
            "data": {
              "type": "services",
              "data": ["Compute", "Object Storage", "Networking", "Database"]
            }
          }
        ]
      }
    ],
    "kind": "task"
  }
}
```

### エラーレスポンス

**Task 失敗** (OCI 認証エラー等):
```json
{
  "jsonrpc": "2.0",
  "id": "req-005",
  "result": {
    "id": "task-uuid",
    "status": {
      "state": "failed",
      "message": {
        "role": "agent",
        "parts": [
          {
            "kind": "data",
            "data": {
              "error_type": "auth_error",
              "message": "OCI authentication failed",
              "guidance": "Check OCI_CONFIG_FILE and OCI_CONFIG_PROFILE environment variables",
              "example_queries": []
            }
          }
        ],
        "messageId": "err-msg-001"
      }
    },
    "kind": "task"
  }
}
```

**JSON-RPC エラー** (プロトコルレベル):
```json
{
  "jsonrpc": "2.0",
  "id": "req-006",
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

## サポートされるメソッド

| メソッド | サポート | 備考 |
|---|---|---|
| `message/send` | Yes | 同期レスポンス |
| `message/stream` | No | streaming=false |
| `tasks/get` | Yes | SDK 自動実装 |
| `tasks/cancel` | No | 同期のため不要 |
| `tasks/resubscribe` | No | streaming=false |
| Push Notification 系 | No | pushNotifications=false |
