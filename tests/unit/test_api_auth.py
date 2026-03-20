"""A2A API キー認証ミドルウェアの単体テスト。"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_oci_client():
    """OCI クライアントのモック。"""
    from unittest.mock import MagicMock

    client = MagicMock()
    client.genai_client = MagicMock()
    client.compartment_id = "test-compartment"
    client.get_available_services.return_value = ["COMPUTE"]
    client.get_available_compartments.return_value = ["root"]
    return client


@pytest.fixture
def app_with_api_key(mock_oci_client):
    """API キー認証有効の FastAPI テストアプリ。"""
    with patch("cost_analyzer.a2a_server._get_oci_client", return_value=mock_oci_client):
        with patch("cost_analyzer.api._get_oci_client", return_value=mock_oci_client):
            with patch(
                "cost_analyzer.api.get_settings"
            ) as mock_settings:
                settings = mock_settings.return_value
                settings.a2a_api_key = "test-secret-key"
                from cost_analyzer.api import app

                yield app


@pytest.fixture
async def client_with_auth(app_with_api_key):
    """httpx AsyncClient for auth testing."""
    transport = ASGITransport(app=app_with_api_key)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestXApiKeyHeader:
    """x-api-key ヘッダー（小文字）での認証テスト。"""

    @pytest.mark.asyncio
    async def test_x_api_key_header_authenticates(self, client_with_auth):
        resp = await client_with_auth.get(
            "/.well-known/agent-card.json",
            headers={"x-api-key": "test-secret-key"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_x_api_key_returns_401(self, client_with_auth):
        resp = await client_with_auth.get(
            "/.well-known/agent-card.json",
            headers={"x-api-key": "wrong-key"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_401(self, client_with_auth):
        resp = await client_with_auth.get("/.well-known/agent-card.json")
        assert resp.status_code == 401


class TestBearerAndXApiKeyCompat:
    """Authorization: Bearer と X-API-Key ヘッダーの互換性テスト。"""

    @pytest.mark.asyncio
    async def test_bearer_token_authenticates(self, client_with_auth):
        resp = await client_with_auth.get(
            "/.well-known/agent-card.json",
            headers={"Authorization": "Bearer test-secret-key"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_uppercase_x_api_key_authenticates(self, client_with_auth):
        resp = await client_with_auth.get(
            "/.well-known/agent-card.json",
            headers={"X-API-Key": "test-secret-key"},
        )
        assert resp.status_code == 200
