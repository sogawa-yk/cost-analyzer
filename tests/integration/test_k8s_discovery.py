"""K8s ディスカバリ規約のマニフェスト準拠テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_K8S_DIR = Path(__file__).resolve().parents[2] / "k8s"
_SERVICE_FILE = _K8S_DIR / "service.yaml"

REQUIRED_LABELS = {
    "a2a.protocol/enabled": "true",
    "a2a.protocol/version": "0.3",
}


@pytest.fixture
def service_manifest() -> dict:
    """k8s/service.yaml を読み込んで返す。"""
    return yaml.safe_load(_SERVICE_FILE.read_text())


class TestServiceLabels:
    """Service マニフェストに A2A ディスカバリ用ラベルが含まれることを検証。"""

    def test_has_a2a_enabled_label(self, service_manifest):
        labels = service_manifest["metadata"]["labels"]
        assert labels.get("a2a.protocol/enabled") == "true"

    def test_has_a2a_version_label(self, service_manifest):
        labels = service_manifest["metadata"]["labels"]
        assert labels.get("a2a.protocol/version") == "0.3"

    def test_has_a2a_port_name(self, service_manifest):
        ports = service_manifest["spec"]["ports"]
        port_names = [p.get("name") for p in ports]
        assert "a2a" in port_names


class TestServiceAnnotations:
    """Service マニフェストにアノテーションが含まれることを検証。"""

    def test_has_description_annotation(self, service_manifest):
        annotations = service_manifest["metadata"].get("annotations", {})
        assert "a2a.protocol/description" in annotations

    def test_agent_card_path_defaults_to_wellknown(self, service_manifest):
        annotations = service_manifest["metadata"].get("annotations", {})
        path = annotations.get(
            "a2a.protocol/agent-card-path",
            "/.well-known/agent-card.json",
        )
        assert path == "/.well-known/agent-card.json"


class TestCustomAgentCardPath:
    """カスタム Agent Card パスのアノテーション仕様検証。"""

    def test_custom_path_annotation_is_valid_key(self):
        key = "a2a.protocol/agent-card-path"
        assert "/" in key
        assert key.startswith("a2a.protocol/")

    def test_custom_path_overrides_default(self):
        custom_manifest = {
            "metadata": {
                "annotations": {
                    "a2a.protocol/agent-card-path": "/custom/agent-card.json",
                },
            },
        }
        annotations = custom_manifest["metadata"]["annotations"]
        path = annotations.get(
            "a2a.protocol/agent-card-path",
            "/.well-known/agent-card.json",
        )
        assert path == "/custom/agent-card.json"

    def test_missing_annotation_uses_default(self):
        manifest_no_annotation = {
            "metadata": {
                "annotations": {},
            },
        }
        annotations = manifest_no_annotation["metadata"]["annotations"]
        path = annotations.get(
            "a2a.protocol/agent-card-path",
            "/.well-known/agent-card.json",
        )
        assert path == "/.well-known/agent-card.json"
