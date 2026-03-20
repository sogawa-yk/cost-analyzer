# Implementation Plan: コンパートメント別集計（group_by）対応

**Branch**: `007-compartment-groupby` | **Date**: 2026-03-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-compartment-groupby/spec.md`

## Summary

コスト集計の軸をサービス固定からユーザー指定可能（サービス別/コンパートメント別）に拡張する。パーサー → モデル → OCIクライアント → 集計エンジン → API → フロントエンドの全レイヤーを貫通する変更。`group_by` フィールドをデフォルト `"service"` で導入し、後方互換性を維持する。修正完了後、K8sクラスタにデプロイして実際のクエリで動作検証し、改善を確認してからPRを作成する。

## Technical Context

**Language/Version**: Python 3.13 (バックエンド), JavaScript ES2022+ (フロントエンド)
**Primary Dependencies**: FastAPI, OCI SDK, Alpine.js 3.x, htmx 2.x, Jinja2, OCI GenAI (LLMパーサー)
**Storage**: N/A（ステートレス）
**Testing**: pytest
**Target Platform**: Linux server (Kubernetes)
**Project Type**: Web application (チャット形式コスト分析ツール)
**Performance Goals**: API 500ms p95, ダッシュボード初期表示 1秒以内
**Constraints**: メモリ 512MB 以下、OCI Usage API レート制限内
**Scale/Scope**: 10,000 コスト明細行まで対応

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | PASS | 既存モジュール構成を踏襲。新規モジュール追加なし。型注釈必須。 |
| II. Testing Standards | PASS | 80%カバレッジ（集計パスは95%）。パーサー・エンジン・APIの各レイヤーにテスト追加。 |
| III. UX Consistency | PASS | i18n対応（compartment_column追加）。テーブルヘッダー動的切替。 |
| IV. Performance Requirements | PASS | OCI API呼び出し回数は変わらない。集計ロジックの計算量も変わらない。 |

## Project Structure

### Documentation (this feature)

```text
specs/007-compartment-groupby/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/cost_analyzer/
├── parser.py            # LLMパーサー（group_by判定ルール追加）
├── models.py            # データモデル（CostQuery.group_by追加、ServiceCost汎用化）
├── engine.py            # 集計エンジン（動的group_by集計）
├── oci_client.py        # OCIクライアント（動的group_byパラメータ）
├── api.py               # HTTPエンドポイント（レスポンスgroup_by対応）
├── static/js/i18n.js    # 翻訳キー追加
└── templates/partials/
    ├── breakdown.html   # 内訳テーブル動的化
    └── comparison.html  # 比較テーブル動的化

tests/
├── conftest.py          # make_cost_query() にgroup_by追加
└── unit/
    ├── test_engine.py   # コンパートメント集計テストケース追加
    └── test_parser.py   # group_byパーステストケース追加
```

**Structure Decision**: 既存のプロジェクト構成を維持。新規ファイル追加なし、既存ファイルの修正のみ。

## Complexity Tracking

> 違反なし — 既存アーキテクチャの拡張のみ。新規抽象化・パターン導入なし。
