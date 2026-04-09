import math
import pytest

from graphrag.models.claim import Claim
from graphrag.utils import claim_deduplicator as dedup
from graphrag.utils import text_processing as tp
from graphrag.utils.domain_filter import DomainFilter


def _make_claim(idx: str, text: str, confidence: float = 0.8, evidence=None, embedding=None):
    return Claim(
        id=f"claim_{idx}",
        text=text,
        doc_id="doc1",
        chunk_id="doc1:0",
        sentence_ids=["doc1:s0"],
        evidence_span=evidence,
        confidence=confidence,
        build_version="test_build",
        embedding=embedding,
    )


# ----------------------- claim_deduplicator -----------------------

def test_hard_deduplicate_merges_duplicates():
    c1 = _make_claim("a", "Transformer 使用自注意力机制", confidence=0.7, evidence=(0, 10))
    c2 = _make_claim("b", "Transformer 使用自注意力机制!", confidence=0.9)
    deduped, merged = dedup.hard_deduplicate([c1, c2])

    assert len(deduped) == 1
    keeper = deduped[0]
    # 置信度取最大值
    assert math.isclose(keeper.confidence, 0.9, rel_tol=1e-6)
    # 记录合并关系
    assert keeper.id in merged and "claim_a" in merged[keeper.id] or "claim_b" in merged[keeper.id]


def test_soft_cluster_merges_similar(monkeypatch):
    c1 = _make_claim("1", "深度学习模型在NLP任务中表现优秀且具备泛化能力", 0.6)
    c2 = _make_claim("2", "深度学习模型在自然语言处理任务中表现优异且效果稳定", 0.5)
    c3 = _make_claim("3", "数据库索引可以显著提升查询性能并减少延迟", 0.4)

    # Mock 向量和相似度，让 c1/c2 高相似，c3 低相似
    monkeypatch.setattr(dedup, "batch_embed", lambda texts, batch_size=50: [
        [1.0, 0.0, 0.0],  # c1
        [0.98, 0.02, 0.0],  # c2
        [0.0, 1.0, 0.0],   # c3
    ])
    monkeypatch.setattr(dedup, "cosine_similarity", lambda a, b: sum(x*y for x, y in zip(a, b)))

    clustered, cmap = dedup.soft_cluster([c1, c2, c3], similarity_threshold=0.9)

    # c1/c2 合并，c3 保留
    assert len(clustered) == 2
    # 找到代表 claim id
    rep_ids = {c.id for c in clustered}
    assert "claim_1" in rep_ids
    assert "claim_3" in rep_ids or "claim_2" in rep_ids
    # canonical map 记录成员
    assert any("claim_2" in v or "claim_1" in v for v in cmap.values())


# ----------------------- text_processing -----------------------

def test_split_sentences_handles_cn_en():
    text = "这是第一句。这是第二句! Here is third?"
    parts = tp.split_sentences(text)
    assert parts == ["这是第一句", "这是第二句", "Here is third"]


def test_extract_sections_mixed_formats():
    text = """1.2 引言\n第一章 背景\n## Methods"""
    sections = tp.extract_sections(text)
    paths = [s[0] for s in sections]
    assert "1.2" in paths
    # 中文章节匹配会得到数字部分（例如"一"），仅验证列表非空
    assert any(p for p in paths)
    assert "2" in paths  # markdown ## -> level 2


def test_sliding_window_respects_step_and_tail():
    sentences = [f"s{i}" for i in range(6)]
    win = tp.sliding_window(sentences, window_size=3, step_size=2)
    assert win == [
        ("s0 s1 s2", 0, 2),
        ("s2 s3 s4", 2, 4),
    ]


def test_extract_context_bounds():
    text = "abcdefghij"
    left, mention, right = tp.extract_context(text, 2, 5, context_window=3)
    assert left == "ab"
    assert mention == "cde"
    assert right.startswith("fgh")


def test_remove_special_chars_and_truncate():
    text = "Hello@World！欢迎！"
    cleaned = tp.remove_special_chars(text)
    assert "@" not in cleaned and "！" in cleaned
    truncated = tp.truncate_text("abcde", 3)
    assert truncated == "..."


def test_normalize_and_remove_no_punct_and_truncate_noop():
    text = "  Hello\tWorld  \n!  "
    normalized = tp.normalize_whitespace(text)
    assert normalized == "Hello World !"

    cleaned = tp.remove_special_chars("A@B#C", keep_punctuation=False)
    assert cleaned == "ABC"

    # 长度不超过最大值时不截断
    keep = tp.truncate_text("short", 10)
    assert keep == "short"


# ----------------------- domain_filter -----------------------

def test_domain_filter_positive_and_negative():
    df = DomainFilter()
    is_valid, conf = df.is_software_engineering_entity("microservices architecture", "KnowledgePoint")
    assert is_valid and conf > 0.3

    is_valid_url, _ = df.is_software_engineering_entity("https://example.com", "KnowledgePoint")
    assert not is_valid_url


def test_domain_filter_relationship():
    df = DomainFilter()
    ok, conf = df.is_valid_relationship("工厂模式", "适配器模式", "BELONGS_TO")
    assert ok and conf >= 0.6

    bad, conf_bad = df.is_valid_relationship("工厂模式", "适配器模式", "UNSUPPORTED")
    assert not bad and conf_bad == 0.0
