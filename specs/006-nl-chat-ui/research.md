# Research: NL チャット UI

**Feature**: 006-nl-chat-ui | **Date**: 2026-03-20

## R1: LLM応答文生成パターン

**Decision**: 既存の `parse_query()` LLMコールとは別に、データ結果取得後に2回目のLLMコールで対話文を生成する。

**Rationale**:
- `parse_query()` は JSON Schema strict mode で構造化出力を返す。自由文テキストを混在させるとスキーマが複雑化し、パース信頼性が低下する
- データ結果（金額、サービス名、変化率）は OCI Usage API 呼び出し後にしか確定しない。パース時点ではデータが未取得のため、応答文を同時生成できない
- 2回目のコールは軽量なテキスト生成（temperature=0.7、max_tokens=256）で、レイテンシ増加は1-2秒程度

**Alternatives considered**:
- パースと応答文を1回のLLMコールで生成 → データ未取得のため不可能
- テンプレートベース → 表現の自然さ・柔軟性が不足（clarifyフェーズで却下済み）
- クライアントサイドLLM → ブラウザ制約・API キー露出リスク

## R2: OCI GenAI モデル選定

**Decision**: `google.gemini-2.5-flash` を使用（既存K8s ConfigMap設定と一致）。

**Rationale**:
- 既存の K8s ConfigMap (`k8s/configmap.yaml`) に `OCI_GENAI_MODEL: "google.gemini-2.5-flash"` が設定済み
- コンパートメントID `ocid1.compartment.oc1..aaaaaaaanxm4oucgt5pkgd7sw2vouvckvvxan7ca2lirowaao7krnzlkdkhq` も設定済み
- ユーザー指示と完全一致。追加設定変更は不要

**Alternatives considered**:
- `meta.llama-3.3-70b-instruct`（現在のデフォルト） → ローカル開発用。本番は gemini-2.5-flash

## R3: チャットUI フロントエンド設計パターン

**Decision**: Alpine.js ストアに `messages` 配列を導入し、各メッセージをオブジェクトとして管理する。既存の `result`/`error`/`clarification` 単一状態を廃止し、メッセージリスト駆動に変更する。

**Rationale**:
- 既存の Alpine.js ストアは単一の結果状態（`result`, `error`, `clarification`）を保持するフラットな構造。チャット形式では複数の結果を時系列で保持する必要があるため、配列ベースに変更が必要
- Alpine.js 3.x の `x-for` ディレクティブでメッセージリストを効率的にレンダリング可能
- htmx は不使用（現在も使用していない — 読み込みのみ）。Alpine.js の `fetch` ベースで完結

**Alternatives considered**:
- htmx の `hx-swap="beforeend"` で追記 → サーバーサイドHTMLレンダリングが必要になり、既存のJSON APIパターンと不整合
- 新規フレームワーク（React/Vue） → 過剰。Alpine.js で十分対応可能

## R4: 応答文生成のシステムプロンプト設計

**Decision**: データ結果の JSON を入力として、対話的な要約文を生成する専用システムプロンプトを新設する。

**Rationale**:
- 既存のパーサー用システムプロンプト（`SYSTEM_PROMPT_TEMPLATE`）はクエリ→JSON変換に特化しており、応答文生成とは目的が異なる
- 応答文プロンプトには以下を含める：
  - データ結果のJSON（型：breakdown or comparison）
  - 言語指定（ja/en）
  - トーン指定（フレンドリー、簡潔、分析的）
  - 出力制約（200文字以内、テーブルデータの重複禁止）

**Alternatives considered**:
- 既存プロンプトの拡張 → 責務が異なるため分離が適切
- Few-shot 例の大量埋め込み → トークン消費が増加、temperature=0.7 で十分な多様性

## R5: ウェルカムメッセージとサジェスト設計

**Decision**: ウェルカムメッセージと質問サジェストは i18n.js の翻訳辞書に定義し、Alpine.js で初期表示する。

**Rationale**:
- LLM で動的生成する必要はない（固定コンテンツ）
- 既存の i18n パターンに従い、日本語/英語の両方を定義
- サジェストはクリック時に `queryText` にセットし、自動送信する

**Alternatives considered**:
- サーバーサイドでウェルカムメッセージを生成 → 不要な API コール
- ハードコード → i18n 非対応になる
