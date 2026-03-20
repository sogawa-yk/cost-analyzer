# Data Model: A2A エージェント Kubernetes サービスディスカバリ

**Date**: 2026-03-19
**Feature**: 004-a2a-k8s-discovery

## 概要

本フィーチャーは規約定義が中心であり、新規の永続化データモデルは導入しない。Kubernetes の既存リソース（Service、Secret）にメタデータを付与する形で実現する。

## エンティティ

### Service ラベル（Kubernetes Service metadata.labels）

| キー | 型 | 必須 | 値 | 説明 |
|------|-----|------|-----|------|
| `a2a.protocol/enabled` | string | Yes | `"true"` | A2A ディスカバリ対象フラグ |
| `a2a.protocol/version` | string | Yes | `"0.3"` 等 | A2A プロトコルバージョン（major.minor） |

### Service アノテーション（Kubernetes Service metadata.annotations）

| キー | 型 | 必須 | デフォルト | 説明 |
|------|-----|------|----------|------|
| `a2a.protocol/agent-card-path` | string | No | `/.well-known/agent-card.json` | Agent Card エンドポイントパス |
| `a2a.protocol/transport` | string | No | `JSONRPC` | トランスポートプロトコル |
| `a2a.protocol/description` | string | No | — | エージェントの説明（日本語可） |

### mini-a2a-auth Secret（Kubernetes Secret）

| キー | 型 | 説明 |
|------|-----|------|
| `api-key` | string (base64) | 全 A2A エージェント共通の API キー |

## 既存エンティティとのマッピング

| K8s リソース | cost-analyzer 設定 | マッピング |
|---|---|---|
| Service ラベル `a2a.protocol/enabled` | — | reporter がディスカバリ時にフィルタ |
| Service ポート `a2a` | FastAPI サーバーポート 8080 | コンテナポートと一致 |
| Secret `mini-a2a-auth` → `api-key` | `A2A_API_KEY` 環境変数 | Deployment で env にマウント済み |
| Agent Card (`/.well-known/agent-card.json`) | a2a-sdk が自動配信 | 変更不要 |

## 状態遷移

本フィーチャーに状態遷移は存在しない。ラベル・アノテーションは静的メタデータであり、デプロイ時に設定される。
