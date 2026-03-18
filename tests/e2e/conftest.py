"""E2E テスト用フィクスチャ: FastAPI サーバーを起動して Playwright に提供する。"""

from __future__ import annotations

import multiprocessing
import time

import pytest
import uvicorn


def _run_server(host: str, port: int) -> None:
    """バックグラウンドプロセスで FastAPI サーバーを起動する。"""
    uvicorn.run("cost_analyzer.api:app", host=host, port=port, log_level="warning")


@pytest.fixture(scope="session")
def base_url():
    """テスト用サーバーの URL を返す。"""
    host = "127.0.0.1"
    port = 8089
    proc = multiprocessing.Process(target=_run_server, args=(host, port), daemon=True)
    proc.start()
    # サーバー起動を待機
    time.sleep(2)
    yield f"http://{host}:{port}"
    proc.terminate()
    proc.join(timeout=5)
