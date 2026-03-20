# Research: コンパートメント別集計（group_by）対応

**Date**: 2026-03-20

## R-001: OCI Usage API の group_by サポート

**Decision**: OCI Usage API の `RequestSummarizedUsagesDetails` は `group_by` パラメータで `compartmentName` をサポートしている。

**Rationale**: Issue レポートで確認済み。`group_by=["compartmentName", "currency"]` で呼び出せば、コンパートメント別のコスト集計がAPI側で行われる。既存の `group_by=["service", "currency"]` と同じパターンで差し替え可能。

**Alternatives considered**:
- クライアント側で `CostLineItem.compartment_name` を使って再集計する方法 → API側で集計する方がデータ量が少なく効率的
- `group_by=["service", "compartmentName", "currency"]` で両方同時に取得 → クロス集計は現時点のスコープ外

## R-002: モデルフィールドの汎用化戦略

**Decision**: `ServiceCost.service` と `ServiceDelta.service` を汎用フィールド名に変更せず、`group_key` フィールドを追加して `service` はエイリアスとして維持する。

**Rationale**: 後方互換性を最大限維持するため。既存コードが `item.service` を参照している箇所が多く、一括リネームはリスクが高い。`group_key` を正規フィールドとし、`service` は `@property` で `group_key` を返すエイリアスとする。API レスポンスでは `group_key` をキーとして返し、フロントエンドは `group_key` を参照する。

**Alternatives considered**:
- `service` を `group_key` に完全リネーム → 後方互換性が崩れる。A2Aエンドポイントなど外部連携にも影響
- 新規モデル `GroupedCost` を作成 → 既存の `ServiceCost` と重複が多く不要な複雑さ

## R-003: パーサーでの集計軸判定

**Decision**: `COST_QUERY_SCHEMA` に `group_by` フィールド（enum: `["service", "compartment"]`）を追加し、`SYSTEM_PROMPT_TEMPLATE` に集計軸判定ルールを追加する。

**Rationale**: 既存の `service_filter` / `compartment_filter` と同じパターンで、LLMにJSON出力の一部として `group_by` を返させる。デフォルトは `"service"`。

**Alternatives considered**:
- ルールベースでキーワード（「コンパートメント別」「部門別」等）をマッチする方法 → LLMの方が自然言語の揺れに強い
- group_by を enum ではなく自由文字列にする → 不正値のリスクが高い

## R-004: フロントエンドのテーブル動的化

**Decision**: API レスポンスに `group_by` フィールドを含め、フロントエンドはこの値に基づいてテーブルヘッダーと表示キーを切り替える。

**Rationale**: バックエンドが集計軸を決定し、フロントエンドはそれに従うだけのシンプルな設計。i18n キーのマッピングも `group_by` 値から直接導出可能（`service` → `service_column`, `compartment` → `compartment_column`）。

**Alternatives considered**:
- フロントエンドで集計軸を判定する方法 → バックエンドとの二重ロジックになる
- テンプレートを集計軸ごとに分離する方法 → テンプレートの重複が増える

## R-005: コンパートメント表示名の解決

**Decision**: Clarification で決定済み。通常は `compartment_name`（リーフ名）を使用し、同名コンパートメントが存在する場合のみ `compartment_path`（フルパス）で区別する。

**Rationale**: ユーザーにとって読みやすいリーフ名をデフォルトとし、曖昧さがある場合のみフルパスにフォールバックする。

**Alternatives considered**: spec の Clarifications セクション参照。

## R-006: デプロイ・検証・PR作成フロー

**Decision**: 実装完了後、Kubernetesクラスタにデプロイし、Issue #7 で言及された操作（「コンパートメント別のコストを教えて」）を実際に実行して動作検証する。改善が確認できればPRを作成し、できなければ修正を繰り返す。

**Rationale**: ユーザーの要求。実環境での動作確認を挟むことで、リリース品質を担保する。

**Alternatives considered**:
- ローカルテストのみでPR作成 → 実環境特有の問題を見逃すリスク
