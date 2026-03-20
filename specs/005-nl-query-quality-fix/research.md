# Research: NL クエリ品質改善

**Date**: 2026-03-20

## Decision 1: 比較クエリ失敗の根本原因と対処方針

**Decision**: システムプロンプト強化 + パーサーでの ValidationError キャッチ＆フォールバックの二段構え

**Rationale**:
- `parser.py` のシステムプロンプト（L16-47）には比較クエリの具体的な JSON 出力例がない。LLM が `comparison_start_date`/`comparison_end_date` を省略する原因
- `CostQuery` の `@model_validator`（`models.py` L59-65）が COMPARISON 時に比較日付を必須としているため、省略時に `ValidationError` が発生
- 現在 `parser.py` L136-147 の `CostQuery()` 構築時に `ValidationError` は `except Exception`（L161）で捕捉され、`map_oci_error()` 経由で `api_error` として返される — これが問題

**Alternatives considered**:
- モデルのバリデーションを緩和する → 却下: 不正データがエンジンに流れるリスク
- 比較クエリを2回のLLM呼び出しに分割 → 却下: レイテンシとコスト倍増

## Decision 2: エッジケース（無関係入力）の対処方針

**Decision**: `parser.py` で `ValidationError` を `json.JSONDecodeError` と同等に扱い、`PARSE_ERROR` + クエリ例として返す

**Rationale**:
- EDGE-01/03/04 の共通原因: LLM がコスト無関係の入力に対して無効な日付（`NoneType`、`start_date >= end_date`）を返す
- 現在は `except Exception` で `map_oci_error()` に渡され、`api_error`（予期しないエラー）として返される
- `pydantic.ValidationError` を明示的に捕捉し、JSON パースエラーと同様の `PARSE_ERROR` + ガイダンスとして返すべき

**Alternatives considered**:
- LLM プロンプトだけで解決 → 却下: LLM の出力は確率的であり、プロンプトだけでは 100% の防御にならない
- `date.fromisoformat()` の前に値チェック → 部分的に有効だが、`ValidationError` 捕捉の方が網羅的

## Decision 3: サービスフィルタの不安定さの対処方針

**Decision**: システムプロンプトに OCI サービス名リスト＋フィルタ抽出の具体例を追加

**Rationale**:
- FLT-01（Compute）は成功、FLT-02（Object Storage）/FLT-03（Database）は失敗
- Compute は単一ワードで明確だが、Object Storage は2語、Database は OCI 上で複数サービス名にマッチしうる
- プロンプトにサービス名リストを提供することで、LLM のマッチング精度を向上

**Alternatives considered**:
- パーサー出力後にサービス名のファジーマッチングを追加 → 補助策として検討可だが、まずプロンプト改善で対応
- OCI API からサービス名を動的取得してプロンプトに注入 → 理想的だがレイテンシ増加。将来の改善候補

## Decision 4: 比較クエリのフォールバック自動推定ロジック

**Decision**: LLM が比較日付を省略した場合、`start_date`/`end_date` から前期間を自動推定する

**Rationale**:
- 「先月と今月を比較して」→ LLM が `start_date=2026-03-01, end_date=2026-04-01` を返した場合、前期間は同じ長さの直前期間（2026-02-01〜2026-03-01）と推定可能
- 自動推定できない場合は `needs_clarification` にフォールバック

**Alternatives considered**:
- 常に確認質問を返す → 却下: ユーザー体験の悪化。「先月と今月を比較して」は意図が明確
