# Tasks: NL チャット UI

**Input**: Design documents from `/specs/006-nl-chat-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: バックエンドモデル追加と Alpine.js ストア基盤の準備

- [x] T001 ConversationalResponse Pydantic モデルを追加する in src/cost_analyzer/models.py
- [x] T002 [P] i18n.js にチャットUI用翻訳キー（ウェルカムメッセージ、サジェスト例、会話クリア、ローディング文言）を追加する in src/cost_analyzer/static/js/i18n.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Alpine.js ストアをメッセージ配列駆動に変更し、チャットレイアウトの骨格を構築する。全ユーザーストーリーがこの基盤に依存する

**CRITICAL**: この Phase 完了前にユーザーストーリーの作業は開始できない

- [x] T003 Alpine.js ストアを messages[] 配列駆動に書き換える（result/clarification/error 状態を廃止し、submitQuery() をメッセージ追加方式に変更）in src/cost_analyzer/static/js/app.js
- [x] T004 index.html をチャットレイアウトに全面書き換え（会話エリア + 固定入力欄）する。x-for でメッセージリストをレンダリングする in src/cost_analyzer/templates/index.html
- [x] T005 チャットメッセージバブルのパーシャルテンプレートを作成する（role による左右配置、タイムスタンプ表示）in src/cost_analyzer/templates/partials/chat-message.html
- [x] T006 チャットUI のベーススタイル（会話エリア、メッセージバブル、入力エリア固定配置、ユーザー/アシスタント色分け）を追加する in src/cost_analyzer/static/css/style.css

**Checkpoint**: チャットレイアウトが表示され、テキストメッセージの送受信（プレーンテキスト応答）が動作する

---

## Phase 3: User Story 1 - チャット形式でコスト問い合わせを行う (Priority: P1) MVP

**Goal**: ユーザーメッセージとシステム応答が時系列のチャットバブルで表示され、ローディング状態と自動スクロールが動作する

**Independent Test**: チャット画面を開き「先月のコストを教えて」と入力して送信し、ユーザーメッセージ（右）とシステム応答（左）が会話形式で表示されることを確認する

### Implementation for User Story 1

- [x] T007 [US1] ローディングインジケーター（タイピングアニメーション）をシステム側メッセージバブルとして表示するロジックを追加する in src/cost_analyzer/static/js/app.js
- [x] T008 [P] [US1] ローディングバブルのアニメーションCSS（ドット点滅アニメーション）を追加する in src/cost_analyzer/static/css/style.css
- [x] T009 [US1] 新しいメッセージ追加時に会話エリアを最下部まで自動スクロールする処理を実装する in src/cost_analyzer/static/js/app.js
- [x] T010 [US1] 処理中は送信ボタンと入力欄を無効化し、応答完了後に再有効化するロジックを実装する in src/cost_analyzer/static/js/app.js
- [ ] T011 [US1] ユニットテスト：Alpine.js ストアの submitQuery() がメッセージ配列にユーザーメッセージとアシスタントメッセージを正しく追加することを検証する in tests/unit/test_api.py

**Checkpoint**: チャット形式でクエリを送信し、プレーンテキスト応答がバブル内に表示される。ローディング・自動スクロール・入力無効化が動作する

---

## Phase 4: User Story 2 - テーブル結果をチャット内で美しく表示する (Priority: P1)

**Goal**: コスト内訳テーブルと比較テーブルがチャットバブル内で美しく整形表示される

**Independent Test**: 「先月と今月のコストを比較して」と送信し、比較テーブルが増減の色分け・通貨フォーマット付きでチャットバブル内に表示される

### Implementation for User Story 2

- [x] T012 [US2] breakdown.html をチャットバブル内用にリファクタリングする（バブルコンテナ内での幅制約、テーブルレスポンシブ対応）in src/cost_analyzer/templates/partials/breakdown.html
- [x] T013 [P] [US2] comparison.html をチャットバブル内用にリファクタリングする（増減色分け維持、トレンドサマリー表示、バブル幅対応）in src/cost_analyzer/templates/partials/comparison.html
- [x] T014 [US2] chat-message.html でメッセージ type に応じて breakdown/comparison パーシャルを条件レンダリングするロジックを追加する in src/cost_analyzer/templates/partials/chat-message.html
- [x] T015 [US2] テーブルのチャットバブル内レスポンシブ対応 CSS（横スクロール、モバイル 375px 対応）を追加する in src/cost_analyzer/static/css/style.css
- [ ] T016 [US2] E2E テスト：内訳クエリと比較クエリの送信でテーブルがチャットバブル内に正しくレンダリングされることを検証する in tests/e2e/test_chat_ui_e2e.py

**Checkpoint**: 内訳テーブル・比較テーブルがチャットバブル内で通貨フォーマット・色分け付きで美しく表示され、モバイルでも読みやすい

---

## Phase 5: User Story 3 - 対話的な応答でユーザーと会話する (Priority: P2)

**Goal**: LLMがデータ結果を踏まえた自然な対話文を生成し、テーブルと共にチャットバブル内に表示される

**Independent Test**: 「先月のコストを教えて」と送信し、テーブルに加えて「最もコストが高いサービスは○○です」のような要約テキストが応答に含まれることを確認する

### Implementation for User Story 3

- [x] T017 [US3] 応答文生成用システムプロンプト（CONVERSATIONAL_PROMPT_TEMPLATE）を定義する。データ結果 JSON・言語・トーン指示・200文字制約を含める in src/cost_analyzer/engine.py
- [x] T018 [US3] generate_conversational_response() 関数を実装する。OCI GenAI を呼び出しデータ結果から対話文を生成する（temperature=0.7, max_tokens=256）in src/cost_analyzer/engine.py
- [x] T019 [US3] /query エンドポイントの breakdown/comparison レスポンスに conversational_text フィールドを追加する。LLM失敗時は null にフォールバックする in src/cost_analyzer/api.py
- [x] T020 [US3] フロントエンドで conversational_text をチャットバブル内のテーブル上部にテキストとして表示するロジックを追加する in src/cost_analyzer/templates/partials/chat-message.html
- [x] T021 [P] [US3] ユニットテスト：generate_conversational_response() のプロンプト構築とレスポンスパースを検証する in tests/unit/test_chat_response.py
- [ ] T022 [P] [US3] 統合テスト：OCI GenAI を呼び出して対話文が生成されることを検証する in tests/integration/test_genai_chat.py

**Checkpoint**: クエリ結果にテーブルと共に自然な対話文が表示される。LLM失敗時はテーブルのみ表示にフォールバックする

---

## Phase 6: User Story 4 - 会話履歴をセッション内で保持する (Priority: P2)

**Goal**: 会話履歴がセッション内で保持され、クリア操作とウェルカムメッセージが機能する

**Independent Test**: 3回連続で質問を送信し、すべての会話が画面上に残っていること、クリアボタンで初期状態に戻ることを検証する

### Implementation for User Story 4

- [x] T023 [US4] ウェルカムメッセージテンプレート（挨拶文 + クリック可能なサジェストチップ）を作成する in src/cost_analyzer/templates/partials/chat-welcome.html
- [x] T024 [US4] Alpine.js ストアの init で messages 配列にウェルカムメッセージを追加し、サジェストクリック時に queryText セット＋自動送信するロジックを実装する in src/cost_analyzer/static/js/app.js
- [x] T025 [US4] 会話クリアボタン（clearMessages メソッド）を実装し、messages 配列をリセットしてウェルカムメッセージを再表示する in src/cost_analyzer/static/js/app.js
- [x] T026 [P] [US4] 会話クリアボタンとウェルカムメッセージのスタイリングを追加する in src/cost_analyzer/static/css/style.css
- [ ] T027 [US4] E2E テスト：複数回の問い合わせ後に全履歴が表示されること、クリアボタンで初期状態に戻ることを検証する in tests/e2e/test_chat_ui_e2e.py

**Checkpoint**: ウェルカムメッセージから始まり、複数回のやり取りが保持され、クリアで初期状態に戻る

---

## Phase 7: User Story 5 - エラー時に対話的にガイドする (Priority: P3)

**Goal**: エラーと確認要求がチャットの流れの中でフレンドリーに表示される

**Independent Test**: 「天気を教えて」と送信し、チャットバブル内にフレンドリーなエラーメッセージとサジェストが表示される

### Implementation for User Story 5

- [x] T028 [US5] error.html をチャットバブル内用にリファクタリングする（フレンドリーなメッセージ、サジェストボタン、リトライ案内をバブル内に表示）in src/cost_analyzer/templates/partials/error.html
- [x] T029 [P] [US5] clarification.html をチャットバブル内用にリファクタリングする（確認質問をバブル内に表示、ユーザーがそのまま回答入力可能）in src/cost_analyzer/templates/partials/clarification.html
- [x] T030 [US5] chat-message.html でエラーと確認メッセージの条件レンダリングを追加する in src/cost_analyzer/templates/partials/chat-message.html
- [x] T031 [US5] エラーメッセージ内のサジェストボタンクリック時に queryText にセット＋送信するロジックを追加する in src/cost_analyzer/static/js/app.js
- [ ] T032 [US5] E2E テスト：無効なクエリ送信時にエラーがチャット形式で表示されサジェストが機能することを検証する in tests/e2e/test_chat_ui_e2e.py

**Checkpoint**: エラー・確認メッセージがチャットの流れの中で自然に表示され、サジェストクリックで再試行できる

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 全ストーリー横断の品質向上

- [ ] T033 [P] 長いクエリ文・大量サービス（20+）のテーブル表示エッジケースを検証し、必要に応じてCSS調整する in src/cost_analyzer/static/css/style.css
- [ ] T034 [P] 入力無効化の解除タイミングが応答表示完了と正しく同期していることを検証する in src/cost_analyzer/static/js/app.js
- [x] T035 既存のユニットテスト（test_api.py, test_ui_routes.py）をチャットUI変更に合わせて更新する in tests/unit/
- [ ] T036 ruff check . でリント違反がないことを確認し修正する
- [ ] T037 quickstart.md の手順に従いローカル環境で全フロー動作確認を実施する

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 依存なし — 即時開始可能
- **Foundational (Phase 2)**: Setup 完了後 — 全ストーリーをブロック
- **US1 (Phase 3)**: Foundational 完了後
- **US2 (Phase 4)**: US1 完了後（チャットバブルにテーブルを埋め込むため）
- **US3 (Phase 5)**: US1 完了後（チャットバブルに対話文を表示するため）。US2 と並列実行可能
- **US4 (Phase 6)**: US1 完了後（messages 配列のウェルカムメッセージ・クリア機能）。US2/US3 と並列実行可能
- **US5 (Phase 7)**: US1 完了後（チャットバブルにエラーを表示するため）。US2/US3/US4 と並列実行可能
- **Polish (Phase 8)**: 全ストーリー完了後

### User Story Dependencies

- **US1 (P1)**: Foundational 完了後に開始。他ストーリーへの依存なし
- **US2 (P1)**: US1 完了が必要（チャットバブル内にテーブルを配置するため）
- **US3 (P2)**: US1 完了が必要。US2 とは独立して実装可能
- **US4 (P2)**: US1 完了が必要。US2/US3 とは独立して実装可能
- **US5 (P3)**: US1 完了が必要。US2/US3/US4 とは独立して実装可能

### Within Each User Story

- テンプレート → CSS → JavaScript → テスト の順序
- バックエンド変更 → フロントエンド変更 の順序

### Parallel Opportunities

- T001 と T002 は並列実行可能（異なるファイル）
- T012 と T013 は並列実行可能（異なるテンプレート）
- US3 完了後、T021 と T022 は並列実行可能（異なるテストファイル）
- US1 完了後、US3/US4/US5 は並列実行可能（異なるファイル群）

---

## Parallel Example: User Story 2

```bash
# テンプレートリファクタリングを並列実行:
Task: "T012 [US2] breakdown.html チャットバブル内用リファクタリング"
Task: "T013 [P] [US2] comparison.html チャットバブル内用リファクタリング"
```

## Parallel Example: User Story 3

```bash
# テストを並列実行:
Task: "T021 [P] [US3] ユニットテスト in tests/unit/test_chat_response.py"
Task: "T022 [P] [US3] 統合テスト in tests/integration/test_genai_chat.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2)

1. Phase 1: Setup を完了
2. Phase 2: Foundational を完了（CRITICAL）
3. Phase 3: US1 を完了 — チャット形式の基本動作を検証
4. Phase 4: US2 を完了 — テーブル表示を検証
5. **STOP and VALIDATE**: チャット形式でテーブル結果が正しく表示されることを確認
6. デプロイ可能な MVP 状態

### Incremental Delivery

1. Setup + Foundational → 基盤完了
2. US1 → テスト → デプロイ（最小チャットUI）
3. US2 → テスト → デプロイ（テーブル表示追加）
4. US3 → テスト → デプロイ（対話的応答追加）
5. US4 → テスト → デプロイ（ウェルカム+クリア追加）
6. US5 → テスト → デプロイ（エラー対話化）
7. Polish → 最終検証

---

## Notes

- [P] tasks = 異なるファイル、依存なし
- [Story] ラベルはユーザーストーリーへのトレーサビリティ
- 各ストーリーは独立して完了・テスト可能
- 既存テスト（test_api.py, test_ui_routes.py）はチャットUI変更に伴い更新が必要（Phase 8 で対応）
- K8s ConfigMap は変更不要（gemini-2.5-flash + コンパートメントID は設定済み）
