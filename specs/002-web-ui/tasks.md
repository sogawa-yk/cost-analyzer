# タスク: Web UI フロントエンド

**入力**: `/specs/002-web-ui/` の設計ドキュメント
**前提条件**: plan.md (必須), spec.md (必須), research.md, data-model.md, contracts/

**テスト**: 憲章 II に基づき、ユニットテスト（80% カバレッジ）と E2E テストを含みます。

**構成**: タスクはユーザーストーリーごとにグループ化され、各ストーリーの独立した実装とテストを可能にします。

## フォーマット: `[ID] [P?] [Story] 説明`

- **[P]**: 並列実行可能（異なるファイル、依存関係なし）
- **[Story]**: このタスクが属するユーザーストーリー（例: US1, US2, US3）
- 正確なファイルパスを説明に含める

---

## フェーズ 1: セットアップ（共通インフラストラクチャ）

**目的**: フロントエンド基盤の初期化、依存関係追加、ディレクトリ構造作成

- [X] T001 pyproject.toml に jinja2>=3.1 依存関係を追加し、uv sync を実行
- [X] T002 src/cost_analyzer/static/ と src/cost_analyzer/templates/ のディレクトリ構造を作成: static/css/, static/js/, static/vendor/, templates/partials/
- [X] T003 [P] Alpine.js 3.x と htmx 2.x の minified ファイルを src/cost_analyzer/static/vendor/ に配置（alpine.min.js, htmx.min.js）
- [X] T004 [P] src/cost_analyzer/templates/base.html にベースレイアウトを作成: HTML5 doctype、meta viewport、Alpine.js/htmx の script タグ、CSS リンク、ヘッダー（アプリ名 + 接続状態 + 言語切替）とメインコンテンツの slot

---

## フェーズ 2: 基盤（ブロッキング前提条件）

**目的**: FastAPI への静的ファイル・テンプレート統合。すべてのユーザーストーリーの前に完了必須

**⚠️ 重要**: このフェーズが完了するまでユーザーストーリーの作業は開始できません

- [X] T005 src/cost_analyzer/api.py に StaticFiles マウント（/static）と Jinja2Templates 初期化を追加、GET / エンドポイントで index.html をレンダリングするルートを追加
- [X] T006 [P] src/cost_analyzer/static/css/style.css にベーススタイルを実装: CSS 変数によるカラーパレット定義（増加=赤 #dc3545、減少=緑 #28a745、エラー=赤、確認=黄 #ffc107）、レスポンシブテーブル（768px ブレークポイント、モバイルで水平スクロール）、ローディングスピナー、ヘッダーレイアウト
- [X] T007 [P] src/cost_analyzer/static/js/i18n.js に i18n モジュールを実装: 日本語/英語の翻訳辞書（data-model.md の I18nResource に準拠）、Alpine.js $store への登録、localStorage による言語設定の永続化と復元、t(key) 翻訳ヘルパー関数
- [X] T008 [P] src/cost_analyzer/static/js/table.js にテーブルユーティリティを実装: Intl.NumberFormat による通貨フォーマット（JPY=小数なし、USD=小数2桁）、割合フォーマット（小数1桁+%）、変化額の符号付きフォーマット
- [X] T009 src/cost_analyzer/static/js/app.js に Alpine.js アプリケーションを実装: AppState ストア（data-model.md に準拠: lang, loading, result, clarification, error, backendHealthy）、クエリ送信関数（POST /query へ fetch、レスポンスタイプに応じた状態更新）、ヘルスチェックポーリング（GET /health を30秒間隔）、エラーハンドリング（ネットワークエラー、HTTPステータス別）
- [X] T010 [P] tests/unit/test_ui_routes.py に GET / エンドポイントのユニットテストを作成: 正常レスポンス 200、テンプレートレンダリングの確認、静的ファイルの配信確認（/static/css/style.css, /static/js/app.js）

**チェックポイント**: 基盤準備完了 — ブラウザで GET / にアクセスするとベースページが表示され、静的ファイルが配信される

---

## フェーズ 3: ユーザーストーリー 1 — 自然言語でコスト内訳を照会する (優先度: P1) 🎯 MVP

**ゴール**: ユーザーがクエリを入力すると、サービス別コスト内訳テーブルが表示される。ローディング状態、clarification、エラーも正しくハンドリングされる。

**独立テスト**: テキスト欄に「先月のサービス別コストを教えて」と入力して送信し、内訳テーブルが金額降順で表示され、合計行が含まれることを確認する。

### ユーザーストーリー 1 のテスト

- [X] T011 [P] [US1] tests/integration/test_ui_rendering.py に内訳テーブルのレンダリングテストを作成: FastAPI TestClient で POST /query をモックし、breakdown レスポンスを返した場合の GET / + JS 状態更新をシミュレート。テンプレートに必要な HTML 要素（テーブル、合計行、期間表示）が含まれることを確認

### ユーザーストーリー 1 の実装

- [X] T012 [US1] src/cost_analyzer/templates/index.html にメインページを実装: base.html を継承、クエリ入力欄（x-model バインド、1000文字 maxlength、プレースホルダーは i18n、空時は送信ボタン disabled）、送信ボタン（loading 中は disabled + スピナー）、x-show による結果エリアの条件分岐（result.type に応じて breakdown/comparison/clarification/error パーシャルを表示）
- [X] T013 [US1] src/cost_analyzer/templates/partials/breakdown.html に内訳テーブルパーシャルを実装: contracts/ui.md に準拠した HTML テーブル（カラム: サービス、金額、割合）、x-for でアイテムをループ、table.js の通貨フォーマット関数で金額を表示、合計行、期間ラベル行
- [X] T014 [US1] src/cost_analyzer/templates/partials/clarification.html に確認メッセージパーシャルを実装: メッセージ表示、提案候補をクリック可能なボタンとして表示（クリックでクエリ欄にセットして再送信）
- [X] T015 [US1] src/cost_analyzer/templates/partials/error.html にエラー表示パーシャルを実装: エラータイプに応じたアイコンとメッセージ、ガイダンステキスト、parse_error 時はクエリ例を表示、api_error 時はリトライボタンを表示
- [X] T016 [US1] T011 のテストを実行し全パスを確認

**チェックポイント**: ユーザーストーリー 1 が完全に機能する状態 — ブラウザでクエリを入力すると内訳テーブルが表示される

---

## フェーズ 4: ユーザーストーリー 2 — コスト比較を視覚的に確認する (優先度: P2)

**ゴール**: 比較クエリを入力すると、2期間のコスト比較テーブルが色分け付きで表示され、トレンドサマリーが自然言語で表示される。

**独立テスト**: 「先月と今月のコストを比較して」と入力し、比較テーブルが表示され、増加が赤系・減少が緑系で色分けされ、トレンドサマリーが下部に表示されることを確認する。

### ユーザーストーリー 2 のテスト

- [X] T017 [P] [US2] tests/integration/test_ui_rendering.py に比較テーブルのレンダリングテストを追加: comparison レスポンス用のテスト、色分け CSS クラスの検証（positive → cost-increase、negative → cost-decrease）、トレンドサマリー要素の存在確認

### ユーザーストーリー 2 の実装

- [X] T018 [US2] src/cost_analyzer/templates/partials/comparison.html に比較テーブルパーシャルを実装: contracts/ui.md に準拠した HTML テーブル（カラム: サービス、前期、当期、変化額、変化率）、x-for でアイテムをループ、absolute_change > 0 なら cost-increase クラス、< 0 なら cost-decrease クラスを適用、合計行（total_change, total_change_percent を表示）、トレンドサマリーパネル（summary テキストを表示）
- [X] T019 [US2] src/cost_analyzer/static/css/style.css に比較テーブル用スタイルを追加: .cost-increase（赤系テキスト + 背景）、.cost-decrease（緑系テキスト + 背景）、トレンドサマリーパネルのスタイル
- [X] T020 [US2] T017 のテストを実行し全パスを確認

**チェックポイント**: ユーザーストーリー 1 と 2 の両方が独立して動作する状態

---

## フェーズ 5: ユーザーストーリー 3 — 日本語と英語を切り替える (優先度: P3)

**ゴール**: 言語切替トグルを操作すると、UIの全テキストが切り替わり、バックエンドへのリクエストに lang パラメータが反映される。設定はブラウザに保存される。

**独立テスト**: 言語トグルを JA → EN に切り替え、全UIラベルが英語になり、クエリ送信時に lang: "en" が送信されることを確認。ページリロード後も EN が保持されることを確認。

### ユーザーストーリー 3 のテスト

- [X] T021 [P] [US3] tests/integration/test_ui_rendering.py に i18n テストを追加: lang パラメータが POST /query リクエストに含まれることの確認、翻訳辞書の ja/en 両方のキーが揃っていることの検証

### ユーザーストーリー 3 の実装

- [X] T022 [US3] src/cost_analyzer/templates/base.html のヘッダーに言語切替トグルを実装: JA/EN ボタン、x-on:click で $store.i18n.setLang() を呼び出し、現在の言語をハイライト表示
- [X] T023 [US3] src/cost_analyzer/templates/ の全テンプレートで i18n 対応: 固定テキストを x-text="$store.i18n.t('key')" に置換、プレースホルダーを x-bind:placeholder に置換、ボタンテキスト・エラーメッセージ等を翻訳キーに対応付け
- [X] T024 [US3] src/cost_analyzer/static/js/app.js のクエリ送信関数に lang パラメータを追加: $store.i18n.currentLang を POST /query の body に含める
- [X] T025 [US3] T021 のテストを実行し全パスを確認

**チェックポイント**: すべてのユーザーストーリーが独立して機能する状態

---

## フェーズ 6: ポリッシュ & 横断的関心事

**目的**: 複数のユーザーストーリーに影響する改善

- [X] T026 [P] Docker イメージをリビルドし、yyz.ocir.io/orasejapan/cost-analyzer:latest にプッシュ。K8s にデプロイして動作確認
- [X] T027 [P] 全テストスイートを実行し、カバレッジレポートを確認: 全体 80% 以上
- [X] T028 [P] ruff リンターを実行し、src/ と tests/ のすべての警告を修正
- [X] T029 quickstart.md をエンドツーエンドで検証: ローカル起動 → ブラウザアクセス → クエリ実行 → 結果表示を確認

---

## 依存関係 & 実行順序

### フェーズ依存関係

- **セットアップ (フェーズ 1)**: 依存関係なし — 即座に開始可能
- **基盤 (フェーズ 2)**: セットアップ完了に依存 — すべてのユーザーストーリーをブロック
- **ユーザーストーリー 1 (フェーズ 3)**: 基盤 (フェーズ 2) に依存
- **ユーザーストーリー 2 (フェーズ 4)**: US1 (フェーズ 3) に依存（index.html の結果エリア構造を使用）
- **ユーザーストーリー 3 (フェーズ 5)**: US1 (フェーズ 3) に依存（テンプレートのテキストを i18n 化）
- **ポリッシュ (フェーズ 6)**: すべてのユーザーストーリー完了に依存

### ユーザーストーリー依存関係

- **ユーザーストーリー 1 (P1)**: 基盤完了後に開始可能 — 他のストーリーへの依存なし
- **ユーザーストーリー 2 (P2)**: US1 完了後に開始可能 — index.html の結果表示エリアに依存
- **ユーザーストーリー 3 (P3)**: US1 完了後に開始可能 — テンプレートの固定テキストを i18n 化

### 並列実行の機会

- T003, T004 はすべて並列実行可能（フェーズ 1）
- T006, T007, T008, T010 はすべて並列実行可能（フェーズ 2 — 異なるファイル）
- T026, T027, T028 はすべて並列実行可能（フェーズ 6）

---

## 実装戦略

### MVP ファースト（ユーザーストーリー 1 のみ）

1. フェーズ 1: セットアップを完了
2. フェーズ 2: 基盤を完了（重要 — すべてのストーリーをブロック）
3. フェーズ 3: ユーザーストーリー 1 を完了（テスト先行）
4. **停止して検証**: ブラウザで「先月のサービス別コストを教えて」を実行し、テーブル表示を確認
5. 準備ができればデプロイ/デモ

### インクリメンタルデリバリー

1. セットアップ + 基盤を完了 → 基盤準備完了
2. ユーザーストーリー 1 を追加 → テストパス確認 → デプロイ/デモ (MVP!)
3. ユーザーストーリー 2 を追加 → テストパス確認 → デプロイ/デモ
4. ユーザーストーリー 3 を追加 → テストパス確認 → デプロイ/デモ
5. 各ストーリーは前のストーリーを壊さずに価値を追加

---

## 注意事項

- [P] タスク = 異なるファイル、依存関係なし
- [Story] ラベルはタスクを特定のユーザーストーリーにマッピング（トレーサビリティ用）
- 各ユーザーストーリーは独立して完了・テスト可能であるべき
- テストを先に書き、実装前にフェイルすることを確認（テスト先行）
- 各タスクまたは論理グループの完了後にコミット
- 任意のチェックポイントで停止してストーリーを独立検証
- カバレッジ目標: 全体 80%
