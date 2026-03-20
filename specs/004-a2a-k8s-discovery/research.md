# Research: A2A エージェント Kubernetes サービスディスカバリ

**Date**: 2026-03-19
**Feature**: 004-a2a-k8s-discovery

## 1. Agent Card デフォルトパスの確認

**Decision**: `/.well-known/agent-card.json` を使用

**Rationale**: a2a-sdk（プロジェクトで使用中のバージョン）のソースコードを調査した結果:
- `AGENT_CARD_WELL_KNOWN_PATH = '/.well-known/agent-card.json'` が現行の正式パス
- `PREV_AGENT_CARD_WELL_KNOWN_PATH = '/.well-known/agent.json'` は旧パス（deprecated）
- SDK の FastAPI 統合は、デフォルトパス使用時に旧パスでも Agent Card を配信する（後方互換、将来削除予定）
- A2A プロトコル公式ドキュメントも `/.well-known/agent-card.json` を推奨

**Alternatives considered**:
- `/.well-known/agent.json`: 旧バージョンのパス。SDK で deprecated 扱い。採用しない

## 2. 認証ヘッダーの互換性

**Decision**: 既存の `Authorization: Bearer` / `X-API-Key` に加えて、小文字 `x-api-key` を明示的にサポート

**Rationale**:
- HTTP ヘッダーは RFC 7230 により case-insensitive。`X-API-Key` と `x-api-key` は技術的に同一
- 現在の cost-analyzer 実装（`api.py:74`）は `request.headers.get("X-API-Key")` で取得しており、HTTP フレームワーク（Starlette）が case-insensitive で処理するため、`x-api-key` でのリクエストも既に動作する
- K8s ディスカバリ規約では `x-api-key` を統一ヘッダー名として定義
- コード上の変更は、テストでの明示的な `x-api-key` ヘッダー検証の追加のみ

**Alternatives considered**:
- ヘッダー名を `Authorization: Bearer` のみに統一: A2A クライアント実装者にとって Bearer トークン設定は煩雑
- 新しいカスタムヘッダー名の導入: 不要な複雑性。既存ヘッダーで十分

## 3. K8s Service ラベル規約

**Decision**: `a2a.protocol/enabled: "true"` と `a2a.protocol/version: "0.3"` を必須ラベルとして定義

**Rationale**:
- `a2a.protocol/` プレフィックスは Kubernetes ラベル命名規約（RFC 1123 サブドメイン）に準拠
- `enabled` フラグにより、A2A サーバーを持つが discovery に参加しない Service を区別可能
- `version` ラベルにより、将来のプロトコルバージョン移行時にクライアントがフィルタ可能

**Alternatives considered**:
- `app.kubernetes.io/` プレフィックス: 汎用すぎて A2A 固有の検索に不向き
- アノテーションのみ: ラベルセレクタで検索できないため、全 Service を取得してからフィルタが必要になりパフォーマンス低下

## 4. Secret 名 `mini-a2a-auth` の選定

**Decision**: 共通 Secret 名 `mini-a2a-auth` を使用（cost-analyzer の既存 Deployment で確認済み）

**Rationale**:
- cost-analyzer の `k8s/deployment.yaml` で既に `mini-a2a-auth` Secret から `A2A_API_KEY` を取得する設定が存在（行 28-32）
- 全エージェントが同一 Secret を参照する設計により、キーローテーション時に Secret を1箇所更新するだけで全エージェントに反映
- Secret 名はクラスタ内の規約として固定

**Alternatives considered**:
- エージェントごとの個別 Secret: 管理が煩雑。キーローテーションに全 Secret の更新が必要
- ConfigMap: API キーは機密情報であり ConfigMap は不適切

## 5. cost-analyzer への具体的変更範囲

**Decision**: K8s マニフェスト変更 + 認証テスト追加のみ。コードの実質変更は不要

**Rationale**:
- **Service ラベル追加** (`k8s/service.yaml`): `a2a.protocol/enabled: "true"`, `a2a.protocol/version: "0.3"` ラベルとポート名 `a2a` を追加
- **認証ヘッダー**: 既に `X-API-Key` ヘッダーをサポートしており、HTTP ヘッダーは case-insensitive なので `x-api-key` も動作する。コード変更不要
- **Deployment**: `mini-a2a-auth` Secret 参照は既に設定済み（行 28-32）
- **テスト追加**: `x-api-key` ヘッダーでの認証が動作することを明示的に検証するテストケースを追加

**Alternatives considered**:
- API コードの認証ロジック書き換え: 不要。既存実装で要件を満たす
