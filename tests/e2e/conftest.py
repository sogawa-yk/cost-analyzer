"""E2E テスト用フィクスチャ。

BASE_URL 環境変数が設定されている場合はそのURLに対してテストを実行する。
未設定の場合はローカルで FastAPI サーバーを起動する。
"""

from __future__ import annotations

import multiprocessing
import os
import time

import pytest
import uvicorn


def _run_server(host: str, port: int) -> None:
    """バックグラウンドプロセスで FastAPI サーバーを起動する。"""
    uvicorn.run("cost_analyzer.api:app", host=host, port=port, log_level="warning")


@pytest.fixture(scope="session")
def base_url():
    """テスト対象の URL を返す。"""
    env_url = os.environ.get("BASE_URL")
    if env_url:
        yield env_url
        return

    host = "127.0.0.1"
    port = 8089
    proc = multiprocessing.Process(target=_run_server, args=(host, port), daemon=True)
    proc.start()
    time.sleep(2)
    yield f"http://{host}:{port}"
    proc.terminate()
    proc.join(timeout=5)
