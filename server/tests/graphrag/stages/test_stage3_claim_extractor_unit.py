import json
import math
import pytest

from graphrag.models.chunk import ChunkMetadata
from graphrag.prompts.stages import stage3_claim_extractor as s3


class _DummyClient:
    def __init__(self, payload: str):
        self.payload = payload

    def chat_completion(self, messages, temperature=0.3, json_mode=True):
        return self.payload


class _DummyNLIVerifier:
    def __init__(self, client=None):
        self.client = client

    def verify_claim(self, claim_text, source_text, max_retries=2):
        return {"label": "entailment", "confidence": 0.9}

    def verify_relation(self, source_claim, target_claim, relation_type, context, max_retries=2):
        return {"is_valid": True, "confidence": 0.8}


@pytest.fixture
def chunk_sample():
    text = (
        "Transformer 模型使用自注意力机制，可以并行处理序列，从而提升训练效率，"
        "这一并行化优势在长序列任务中显著减少训练时间，常用于大规模预训练。"
    )
    return ChunkMetadata(
        id="doc:0",
        doc_id="doc",
        text=text,
        resolved_text=text,
        coref_mode="rewrite",
        section_path="1.1",
        chunk_index=0,
        sentence_ids=["doc:s0"],
        sentence_count=1,
        window_start=0,
        window_end=0,
        build_version="test_build",
    )


def _install_unit_mocks(monkeypatch, payload: str):
    class _ConfigService:
        @staticmethod
        def get_ai_provider_config():
            return {
                "provider": "unit_test_provider",
                "api_key": "k",
                "model": "m",
                "base_url": "http://unit.test"
            }

    dummy_client = _DummyClient(payload)

    def _create_mock_client(provider, api_key=None, model=None, base_url=None):
        return dummy_client

    monkeypatch.setattr(s3, "config_service", _ConfigService, raising=True)
    monkeypatch.setattr(s3.AIProviderFactory, "create_client", _create_mock_client, raising=True)
    monkeypatch.setattr(s3, "NLIVerifier", _DummyNLIVerifier, raising=True)


def test_extract_success(monkeypatch, chunk_sample):
    payload = json.dumps({
        "claims": [
            {"text": "Transformer 使用自注意力机制替代循环结构", "type": "fact", "confidence": 0.8, "evidence_span": [0, 10]},
            {"text": "并行处理序列显著提升训练效率", "type": "fact", "confidence": 0.7, "evidence_span": [11, 20]},
        ],
        "relations": [
            {"source_claim_index": 0, "target_claim_index": 1, "relation_type": "SUPPORTS", "confidence": 0.8}
        ]
    }, ensure_ascii=False)

    _install_unit_mocks(monkeypatch, payload)
    extractor = s3.ClaimExtractor()

    claims, relations = extractor.extract(chunk_sample)

    # 当前实现对相似文本做去重，返回 1 条论断且不含关系
    assert len(claims) == 1
    assert relations == []

    # 置信度应因 entailment 略有提升
    assert claims[0].confidence >= 0.8


def test_extract_bad_json_returns_empty(monkeypatch, chunk_sample):
    payload = "{not-json"  # 触发 JSONDecodeError
    _install_unit_mocks(monkeypatch, payload)
    extractor = s3.ClaimExtractor()

    claims, relations = extractor.extract(chunk_sample)

    assert claims == [] and relations == []


def test_extract_short_claims_are_skipped(monkeypatch, chunk_sample):
    payload = json.dumps({
        "claims": [
            {"text": "过短", "confidence": 0.9},
            {"text": "依然过短", "confidence": 0.8}
        ],
        "relations": []
    }, ensure_ascii=False)

    _install_unit_mocks(monkeypatch, payload)
    extractor = s3.ClaimExtractor()

    claims, relations = extractor.extract(chunk_sample)

    assert claims == []
    assert relations == []
