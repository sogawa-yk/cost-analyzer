# Implementation Plan: A2A エージェント Kubernetes サービスディスカバリ

**Branch**: `004-a2a-k8s-discovery` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-a2a-k8s-discovery/spec.md`

## Summary

Kubernetes クラスタ内の A2A 対応エージェントをラベル・アノテーション規約で自動検出可能にする。cost-analyzer の既存 K8s マニフェスト（Service/Deployment）に A2A ディスカバリ用ラベル・アノテーションと認証 Secret 参照を追加する。コード変更は最小限（認証ヘッダー `x-api-key` の追加サポート）。主な成果物はマニフェスト変更とディスカバリ規約ドキュメント。

## Technical Context

**Language/Version**: Python 3.13（既存バックエンド）、YAML（K8s マニフェスト）
**Primary Dependencies**: FastAPI（既存）、a2a-sdk（既存）
**Storage**: N/A（ステートレス）
**Testing**: pytest（既存テストスイート）
**Target Platform**: Kubernetes（OKE）上のコンテナ
**Project Type**: Web service（既存）+ インフラ規約定義
**Performance Goals**: ディスカバリ 10 秒以内（SC-002）、API レスポンス 500ms p95 以内（Constitution IV）
**Constraints**: メモリ 512Mi 以下（既存制約）、既存 CLI/Web UI/API の動作維持
**Scale/Scope**: 10 エージェント以上のクラスタ内ディスカバリ

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | PASS | 認証ミドルウェアへの小規模変更のみ。40行/400行制限内 |
| II. Testing Standards | PASS | 認証ヘッダー追加の単体テスト・統合テストを追加 |
| III. UX Consistency | PASS | ユーザー向け UI 変更なし。エラーメッセージは既存形式を踏襲 |
| IV. Performance Requirements | PASS | 既存パフォーマンス特性への影響なし |
| Quality Gates | PASS | Lint/Test/Performance gate すべて適用可能 |

## Project Structure

### Documentation (this feature)

```text
specs/004-a2a-k8s-discovery/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── k8s-discovery.md # K8s ラベル・アノテーション規約
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
k8s/
├── deployment.yaml      # 変更: Secret マウント確認（既存済み）
└── service.yaml         # 変更: A2A ラベル・アノテーション追加

src/cost_analyzer/
└── api.py               # 変更: x-api-key ヘッダーサポート追加

tests/
├── unit/
│   └── test_api_auth.py # 新規: x-api-key ヘッダー認証テスト
└── integration/
    └── test_a2a.py      # 変更: x-api-key ヘッダーテスト追加
```

**Structure Decision**: 既存プロジェクト構造をそのまま使用。K8s マニフェスト変更と認証ミドルウェアの小規模拡張のみ。

## Complexity Tracking

> 違反なし。新規プロジェクトやパターンの追加は不要。
