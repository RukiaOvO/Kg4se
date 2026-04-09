import json
import pytest

from graphrag.prompts.stages import stage4_theme_builder as s4
from graphrag.models.theme import Theme


class _DummyClient:
    def __init__(self, payload: str):
        self.payload = payload

    def chat_completion(self, messages, temperature=0.2, json_mode=True):
        return self.payload


def _install_theme_mocks(monkeypatch, payload: str):
    class _ConfigService:
        @staticmethod
        def get_ai_provider_config():
            return {"provider": "unit", "api_key": "k", "model": "m", "base_url": "http://unit"}

    dummy_client = _DummyClient(payload)

    def _create_mock_client(provider, api_key=None, model=None, base_url=None):
        return dummy_client

    monkeypatch.setattr(s4, "config_service", _ConfigService, raising=True)
    monkeypatch.setattr(s4.AIProviderFactory, "create_client", _create_mock_client, raising=True)


def test_theme_builder_success(monkeypatch):
    payload = json.dumps({"themes": []})

    _install_theme_mocks(monkeypatch, payload)
    builder = s4.ThemeBuilder()
    builder.thresholds["multi_scale"] = {"enabled": False}
    builder.thresholds["min_community_size"] = 1

    monkeypatch.setattr(builder, "_create_concept_graph", lambda graph_name, doc_id: None)
    monkeypatch.setattr(builder, "_drop_graph", lambda graph_name: None)
    monkeypatch.setattr(builder, "_detect_communities", lambda graph_name, doc_id: {1: ["c1", "c2", "c3"], 2: ["c4", "c5", "c6"]})

    dummy_themes = [
        Theme(
            id="t1",
            label="切块处理",
            summary=(
                "GraphRAG 通过切块降低上下文长度并方便并行处理，从而提升推理效率和召回，"
                "切块后的文本还能减少无关信息干扰，为后续社区检测打下基础。"
            ),
            level=1,
            keywords=["切块", "并行", "上下文"],
            member_count=3,
            concept_ids=["c1"],
            claim_ids=["cl1"],
            build_version="test_build",
        ),
        Theme(
            id="t2",
            label="关系抽取",
            summary=(
                "多阶段管道抽取概念和关系，构建知识图谱并支撑查询和可视化，"
                "在高置信度抽取基础上再做主题聚合，保证结构质量。"
            ),
            level=1,
            keywords=["关系", "知识图谱"],
            member_count=3,
            concept_ids=["c2"],
            claim_ids=["cl2"],
            build_version="test_build",
        ),
    ]
    monkeypatch.setattr(
        builder,
        "_batch_create_themes",
        lambda theme_data_list, doc_id, build_version: dummy_themes,
    )

    themes = builder.build(doc_id="doc", build_version="test_build")

    assert len(themes) == 2
    assert themes[0].label == "切块处理"


def test_theme_builder_empty_communities(monkeypatch):
    payload = "{}"
    _install_theme_mocks(monkeypatch, payload)
    builder = s4.ThemeBuilder()
    builder.thresholds["multi_scale"] = {"enabled": False}
    builder.thresholds["min_community_size"] = 1

    monkeypatch.setattr(builder, "_create_concept_graph", lambda graph_name, doc_id: None)
    monkeypatch.setattr(builder, "_drop_graph", lambda graph_name: None)
    monkeypatch.setattr(builder, "_detect_communities", lambda graph_name, doc_id: {})
    monkeypatch.setattr(
        builder,
        "_batch_create_themes",
        lambda theme_data_list, doc_id, build_version: [],
    )

    themes = builder.build(doc_id="doc", build_version="test_build")

    assert themes == []
