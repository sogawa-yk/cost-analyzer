# Tasks: A2A エージェント Kubernetes サービスディスカバリ

**Input**: Design documents from `/specs/004-a2a-k8s-discovery/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/k8s-discovery.md

**Tests**: テスト追加あり（Constitution II: Testing Standards に準拠）

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: 既存プロジェクトへの追加変更準備

- [x] T001 ブランチ `004-a2a-k8s-discovery` の最新状態を確認し、`main` からのリベースまたはマージを実施

**Checkpoint**: ブランチが最新状態で、既存テストがすべてパスする

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 全ユーザーストーリーに共通するインフラ変更

**⚠️ CRITICAL**: ユーザーストーリーの作業開始前に完了必須

- [x] T002 `k8s/service.yaml` に A2A ディスカバリ用ラベル（`a2a.protocol/enabled: "true"`, `a2a.protocol/version: "0.3"`）、アノテーション（`a2a.protocol/description`）、ポート名（`a2a`）を追加
- [x] T003 [P] `k8s/deployment.yaml` の `mini-a2a-auth` Secret マウントと `A2A_API_KEY` 環境変数が正しく設定されていることを確認・ドキュメント化

**Checkpoint**: `kubectl apply -f k8s/` で A2A ラベル付き Service がデプロイされ、`kubectl get svc -l a2a.protocol/enabled=true` で検出できる

---

## Phase 3: User Story 1 — Kubernetes クラスタ内の A2A エージェントを自動検出する (Priority: P1) 🎯 MVP

**Goal**: A2A ラベル付き Service が reporter から自動検出可能になる

**Independent Test**: `kubectl get svc -l a2a.protocol/enabled=true` で cost-analyzer Service が検出され、Agent Card が取得できること

### Tests for User Story 1

- [x] T004 [P] [US1] `tests/integration/test_a2a.py` に Agent Card エンドポイント `GET /.well-known/agent-card.json` がディスカバリ規約に準拠した Agent Card（name, description, skills[], protocolVersion）を返すことを検証するテストを追加
- [x] T005 [P] [US1] `tests/integration/test_k8s_discovery.py` を新規作成し、K8s Service マニフェスト（`k8s/service.yaml`）に必須ラベル `a2a.protocol/enabled` と `a2a.protocol/version` が含まれることを YAML パースで検証するテストを作成

### Implementation for User Story 1

- [x] T006 [US1] K8s Service マニフェストの変更をクラスタに適用し、`kubectl get svc -l a2a.protocol/enabled=true` で cost-analyzer が検出されることを手動検証

**Checkpoint**: cost-analyzer が A2A ラベル付き Service として検出可能。Agent Card がプロトコル準拠で取得可能

---

## Phase 4: User Story 2 — 共通 API キーによるエージェント間認証 (Priority: P2)

**Goal**: `x-api-key` ヘッダーでの認証が明示的にサポートされ、テストで保証される

**Independent Test**: `x-api-key` ヘッダーで正しい/不正な API キーを送信し、認証の成否が期待通りであること

### Tests for User Story 2

- [x] T007 [P] [US2] `tests/unit/test_api_auth.py` を新規作成し、`A2AApiKeyMiddleware` が `x-api-key` ヘッダー（小文字）での認証を正しく処理することを検証するテストを作成（正常認証、不正キー拒否、キーなし拒否の 3 ケース）
- [x] T008 [P] [US2] `tests/integration/test_a2a.py` に `x-api-key` ヘッダーでの A2A エンドポイント認証テストを追加（`POST /a2a` と `GET /.well-known/agent-card.json` の両方）

### Implementation for User Story 2

- [x] T009 [US2] `src/cost_analyzer/api.py` の `A2AApiKeyMiddleware` で `x-api-key` ヘッダー（小文字）を明示的に取得対象に追加（`X-API-Key` に加えて `x-api-key` のフォールバック。HTTP フレームワークが case-insensitive で処理するため動作確認が主目的）

**Checkpoint**: `x-api-key` ヘッダーでの認証が単体テスト・統合テストの両方でパス

---

## Phase 5: User Story 3 — 既存エージェントの移行とカスタム設定 (Priority: P3)

**Goal**: 既存の cost-analyzer Service にラベルを追加するだけでディスカバリ対応が完了し、カスタムパスも動作すること

**Independent Test**: ラベル追加前後で `kubectl get svc -l a2a.protocol/enabled=true` の結果が変化し、Agent Card が取得可能であること

### Tests for User Story 3

- [x] T010 [P] [US3] `tests/integration/test_k8s_discovery.py` に、Service アノテーション `a2a.protocol/agent-card-path` でカスタムパスが指定可能であること（マニフェストの YAML パースによるバリデーション）のテストを追加

### Implementation for User Story 3

- [x] T011 [US3] `specs/004-a2a-k8s-discovery/quickstart.md` の手順に従い、既存 cost-analyzer Service への `kubectl label` / `kubectl annotate` によるラベル・アノテーション追加を手動実行し、動作を検証

**Checkpoint**: 既存 Service へのラベル追加で自動検出が動作。カスタムパスアノテーションが仕様に記載

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: ドキュメント整備と全体検証

- [x] T012 [P] `specs/003-agent-interop/spec.md` および `specs/003-agent-interop/contracts/a2a.md` に K8s ディスカバリ規約（`specs/004-a2a-k8s-discovery/contracts/k8s-discovery.md`）への相互参照を追加
- [x] T013 [P] `specs/004-a2a-k8s-discovery/quickstart.md` の全手順を実環境で実行し、動作を検証
- [x] T014 既存テストスイート（`tests/`）を実行し、全テストがパスすることを確認（リグレッションなし）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 と US2 は並行実行可能（異なるファイルを変更）
  - US3 は US1 完了後が望ましい（ラベル追加の動作検証のため）
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 完了後に開始可能。他ストーリーへの依存なし
- **User Story 2 (P2)**: Foundational 完了後に開始可能。US1 と並行実行可能
- **User Story 3 (P3)**: US1 完了後が望ましい（検出の動作確認を前提）

### Within Each User Story

- テストを先に作成し、FAIL を確認してから実装
- マニフェスト変更 → テスト → 手動検証の順

### Parallel Opportunities

- T004, T005 は並行実行可能（異なるテストファイル）
- T007, T008 は並行実行可能（異なるテストファイル）
- US1 と US2 は並行実行可能
- T012, T013 は並行実行可能

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "test_api_auth.py — x-api-key 認証単体テスト"
Task: "test_a2a.py — x-api-key 認証統合テスト"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (K8s マニフェスト変更)
3. Complete Phase 3: User Story 1 (ディスカバリ検証)
4. **STOP and VALIDATE**: `kubectl get svc -l a2a.protocol/enabled=true` で検出確認
5. Deploy if ready

### Incremental Delivery

1. Setup + Foundational → K8s マニフェスト変更完了
2. User Story 1 → ディスカバリ動作確認 → Deploy (MVP!)
3. User Story 2 → `x-api-key` 認証テスト追加 → Deploy
4. User Story 3 → 移行手順検証 → Deploy
5. Polish → ドキュメント相互参照・全体検証

---

## Notes

- 本フィーチャーのコード変更は最小限（認証ヘッダーのテスト追加が主）
- 主な成果物は K8s マニフェスト変更とディスカバリ規約ドキュメント
- 既存の `k8s/deployment.yaml` は `mini-a2a-auth` Secret 参照が既に設定済みのため変更不要
- HTTP ヘッダーは case-insensitive（RFC 7230）のため `x-api-key` は既存の `X-API-Key` 処理で動作する
