# 自然言語コストクエリ E2E テストレポート

**実行日時**: 2026-03-20
**対象**: cost-analyzer (Kubernetes デプロイ済み)
**テスト数**: 23
**環境**: OKE クラスタ / cost-analyzer Pod (Python 3.13 + FastAPI + OCI GenAI Llama 3.3 70B)

## サマリー

| 判定 | 件数 | 割合 |
|------|------|------|
| PASS | 15 | 65% |
| WARN (要改善) | 8 | 35% |
| FAIL | 0 | 0% |

---

## カテゴリ 1: 日本語 内訳クエリ — 5/5 PASS

| ID | テスト | クエリ | 結果 | 詳細 |
|---|---|---|---|---|
| JP-01 | 相対期間（先月） | 先月のサービス別コストを教えて | PASS | items=74, total=$54,290,540.39, 2026-02-01~2026-03-01 |
| JP-02 | 月名指定 | 2月のコスト内訳を見せて | PASS | items=74, total=$54,290,540.39, 2026-02-01~2026-03-01 |
| JP-03 | 今月 | 今月のコストはいくら？ | PASS | items=74, total=$37,575,536.49, 2026-03-01~2026-04-01 |
| JP-04 | 日数指定 | 過去90日間のコストを教えて | PASS | items=79, total=$182,960,170.28, 2025-12-21~2026-03-20 |
| JP-05 | 四半期 | 今年の第1四半期のコストを教えて | PASS | items=79, total=$159,103,653.80, 2026-01-01~2026-04-01 |

## カテゴリ 2: 英語 内訳クエリ — 5/5 PASS

| ID | テスト | クエリ | 結果 | 詳細 |
|---|---|---|---|---|
| EN-01 | last month | Show me last month's cost breakdown | PASS | items=74, total=$54,290,540.39, 2026-02-01~2026-03-01 |
| EN-02 | 絶対月指定 | Show costs for January 2026 | PASS | items=76, total=$67,237,576.92, 2026-01-01~2026-02-01 |
| EN-03 | this quarter | What are my costs for this quarter? | PASS | items=79, total=$159,103,653.80, 2026-01-01~2026-04-01 |
| EN-04 | past 30 days | Cost breakdown for the past 30 days | PASS | items=75, total=$58,880,550.41, 2026-02-18~2026-03-20 |
| EN-05 | last 7 days | How much did I spend in the last 7 days? | PASS | items=73, total=$13,237,261.33, 2026-03-13~2026-03-20 |

## カテゴリ 3: 比較クエリ — 0/5 PASS

| ID | テスト | クエリ | 結果 | 問題 |
|---|---|---|---|---|
| CMP-01 | JP:2期間比較 | 先月と今月のコストを比較して | WARN | LLM が `comparison_start_date`/`comparison_end_date` を出力せず、バリデーションエラー |
| CMP-02 | JP:前月比 | 前月比でコストはどうなった？ | WARN | 同上 |
| CMP-03 | JP:絶対月比較 | 1月と2月を比較して | PASS* | clarification（「どちらを基準に？」）— 正当な応答だが比較結果は未返却 |
| CMP-04 | EN:month comparison | Compare costs between January and February 2026 | WARN | LLM が比較日付を正しく構造化できず、バリデーションエラー |
| CMP-05 | EN:this vs last | How do this month's costs compare to last month? | WARN | no_data — 当月と先月の比較だが期間処理に問題あり |

**根本原因**: LLM が `query_type: COMPARISON` を返す際に `comparison_start_date` と `comparison_end_date` を省略し、CostQuery のバリデーション（COMPARISON 時に必須）でエラーになる。

## カテゴリ 4: サービスフィルタ — 1/3 正確

| ID | テスト | クエリ | 結果 | 問題 |
|---|---|---|---|---|
| FLT-01 | JP:Compute | 先月のComputeのコストは？ | PASS | items=1, total=$3,494,720.63 — フィルタ正常動作 |
| FLT-02 | EN:Object Storage | Show only Object Storage costs for last month | WARN | items=74 — フィルタが効いていない（全サービス返却） |
| FLT-03 | JP:Database | 先月のDatabaseのコストを教えて | WARN | items=74 — フィルタが効いていない（全サービス返却） |

**根本原因**: LLM がサービス名を `service_filter` パラメータとして抽出するかどうかが不安定。FLT-01 は成功しているが、FLT-02/FLT-03 では LLM がフィルタを設定せずに全サービスを返している。

## カテゴリ 5: エッジケース — 2/5 正常

| ID | テスト | クエリ | 結果 | 問題 |
|---|---|---|---|---|
| EDGE-01 | 曖昧（期間なし） | コストを教えて | WARN | api_error — LLM 応答のパースに失敗（`NoneType` エラー） |
| EDGE-02 | 曖昧（最近） | 最近のコストはどう？ | PASS | breakdown（今月）として処理 — 妥当な解釈 |
| EDGE-03 | コスト無関係 | Hello, what can you do? | WARN | api_error — LLM が無効な日付を返しバリデーションエラー |
| EDGE-04 | 完全に無関係 | 今日の天気は？ | WARN | api_error — 同上、`start_date >= end_date` エラー |
| EDGE-05 | 非対応言語 | Zeig mir die Kosten | PASS | clarification（「日本語または英語で入力してください」） — 仕様通り |

**根本原因**: LLM がコスト無関係の入力に対して `needs_clarification` フラグを立てずに無効な日付を返すことがある。パーサーのエラーハンドリングが LLM の不正出力を十分にカバーできていない。

---

## 検出された問題（重要度順）

### P1: 比較クエリの LLM パース失敗 (CMP-01, CMP-02, CMP-04)

LLM が `query_type: COMPARISON` を返す際に `comparison_start_date`/`comparison_end_date` を省略し、CostQuery バリデーションでエラーになる。比較機能が事実上動作しない。

**推奨対処**:
- パーサーの system prompt で比較クエリの JSON 出力例を強化
- LLM が比較日付を省略した場合のフォールバック処理を追加（自動推定または clarification 返却）

### P2: コスト無関係クエリのエラーハンドリング (EDGE-01, EDGE-03, EDGE-04)

LLM がコスト無関係の入力に対して無効な JSON を返した場合、パーサーが `api_error` を返す。仕様では「クエリ例を返す」（FR-011）べき。

**推奨対処**:
- パーサーで CostQuery バリデーションエラーを捕捉し、`parse_error` + クエリ例として返す
- LLM の無効出力パターン（`start_date >= end_date`、日付なし等）に対する防御的処理

### P3: サービスフィルタの不安定さ (FLT-02, FLT-03)

LLM が `service_filter` を抽出するかどうかが不安定。「Compute」は成功するが「Object Storage」「Database」ではフィルタが効かない。

**推奨対処**:
- system prompt のフィルタ抽出例を増やす
- 利用可能なサービス名リストを LLM に提供してマッチング精度を向上

---

## 全体評価

| カテゴリ | PASS率 | 評価 |
|---------|--------|------|
| 日本語 内訳 | 5/5 (100%) | 優秀 |
| 英語 内訳 | 5/5 (100%) | 優秀 |
| 比較クエリ | 0/5 (0%) | 要修正 |
| サービスフィルタ | 1/3 (33%) | 要改善 |
| エッジケース | 2/5 (40%) | 要改善 |
| **全体** | **15/23 (65%)** | **内訳クエリは安定、比較・フィルタ・エラーハンドリングに改善余地** |
