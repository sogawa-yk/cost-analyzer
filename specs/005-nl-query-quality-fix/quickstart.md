# Quickstart: NL クエリ品質改善

## 概要

E2E テスト（2026-03-20）で発見された 8 件の WARN を修正し、PASS 率を 65% → 90% 以上に引き上げる。

## 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/cost_analyzer/parser.py` | システムプロンプト強化、ValidationError ハンドリング、比較日付フォールバック |
| `tests/unit/test_parser.py` | 新規テストケース追加（比較フォールバック、エッジケース、サービスフィルタ） |

## 前提条件

- Python 3.13
- OCI 認証情報設定済み
- `pip install -e .` でプロジェクトインストール済み

## テスト実行

```bash
# ユニットテスト
pytest tests/unit/test_parser.py -v

# 全ユニットテスト
pytest tests/unit/ -v
```

## 修正概要

### P1: 比較クエリ修正
- システムプロンプトに比較クエリの JSON 出力例を追加
- LLM が比較日付を省略した場合、`start_date`/`end_date` から前期間を自動推定

### P2: エッジケース修正
- `pydantic.ValidationError` を明示的に捕捉
- `api_error` ではなく `parse_error` + クエリ例として返却

### P3: サービスフィルタ修正
- システムプロンプトに OCI サービス名リストと抽出例を追加
