"""
Additional tests for low-coverage utils modules
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from graphrag.utils.nli_verifier import NLIVerifier
from graphrag.utils.embedding import cosine_similarity
from graphrag.utils.domain_filter import DomainFilter


class TestNLIVerifier:
    """Test NLIVerifier for increased coverage."""
    
    @pytest.fixture
    def nli_verifier(self):
        verifier = NLIVerifier(client=None)
        return verifier
    
    def test_verify_claim_entailment(self, nli_verifier):
        """Test claim verification with entailment."""
        result = nli_verifier.verify_claim("AI is smart", source_text="Artificial Intelligence is intelligent")
        assert "label" in result
        assert result["label"] in ["entailment", "contradiction", "neutral"]
        assert "confidence" in result
    
    def test_verify_claim_contradiction(self, nli_verifier):
        """Test claim verification with contradiction."""
        result = nli_verifier.verify_claim("AI is dumb", source_text="Artificial Intelligence is intelligent")
        assert "label" in result
        assert result["label"] in ["entailment", "contradiction", "neutral"]
    
    def test_verify_claim_neutral(self, nli_verifier):
        """Test claim verification with neutral result."""
        result = nli_verifier.verify_claim("Weather is nice", source_text="AI is smart")
        assert "label" in result
        assert result["label"] in ["entailment", "contradiction", "neutral"]
    
    def test_verify_relation_valid(self, nli_verifier):
        """Test relation verification with valid result."""
        result = nli_verifier.verify_relation(
            "Concept A is defined", 
            "Concept B is defined",
            "SUPPORTS",
            context="Both related to topic X"
        )
        assert "is_valid" in result
        assert isinstance(result["is_valid"], bool)
        assert "confidence" in result
    
    def test_verify_relation_invalid(self, nli_verifier):
        """Test relation verification with invalid result."""
        result = nli_verifier.verify_relation(
            "Concept A",
            "Concept B",
            "CONTRADICTS",
            context="Context text"
        )
        assert "is_valid" in result
        assert isinstance(result["is_valid"], bool)
    
    def test_verify_claim_max_retries(self, nli_verifier):
        """Test claim verification retry logic."""
        result = nli_verifier.verify_claim("Test", source_text="Test context", max_retries=3)
        assert result is not None
        assert "label" in result


class TestEmbeddingAdvanced:
    """Advanced tests for embedding utilities."""
    
    def test_cosine_similarity_with_large_vectors(self):
        """Test cosine similarity with high-dimensional vectors."""
        v1 = [float(i) for i in range(100)]
        v2 = [float(i) for i in range(100)]
        sim = cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 1e-6
    
    def test_cosine_similarity_negative_values(self):
        """Test cosine similarity with negative values."""
        v1 = [-1.0, -1.0, 0.0]
        v2 = [-1.0, -1.0, 0.0]
        sim = cosine_similarity(v1, v2)
        assert abs(sim - 1.0) < 1e-6
    
    def test_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        v1 = [0.0, 0.0, 0.0]
        v2 = [1.0, 1.0, 1.0]
        sim = cosine_similarity(v1, v2)
        assert sim == 0.0


class TestDomainFilter:
    """Test DomainFilter for increased coverage."""
    
    @pytest.fixture
    def domain_filter(self):
        return DomainFilter()
    
    def test_domain_filter_initialization(self, domain_filter):
        """Test DomainFilter can be initialized."""
        assert domain_filter is not None
        assert domain_filter.keywords is not None
        assert domain_filter.excluded is not None
    
    def test_is_software_engineering_entity_positive(self, domain_filter):
        """Test is_software_engineering_entity with positive examples."""
        is_valid, confidence = domain_filter.is_software_engineering_entity("singleton pattern", "KnowledgePoint")
        assert is_valid is True
        assert confidence > 0.0
    
    def test_is_software_engineering_entity_negative(self, domain_filter):
        """Test is_software_engineering_entity with negative examples."""
        is_valid, confidence = domain_filter.is_software_engineering_entity("random weather", "KnowledgePoint")
        assert is_valid is False
    
    def test_is_software_engineering_entity_empty(self, domain_filter):
        """Test is_software_engineering_entity with empty string."""
        is_valid, confidence = domain_filter.is_software_engineering_entity("", "KnowledgePoint")
        assert is_valid is False
        assert confidence == 0.0
    
    def test_is_valid_relationship_valid(self, domain_filter):
        """Test is_valid_relationship with valid relationship."""
        is_valid, confidence = domain_filter.is_valid_relationship(
            "singleton pattern",
            "factory pattern",
            "BELONGS_TO",
            "KnowledgePoint",
            "KnowledgePoint"
        )
        assert isinstance(is_valid, bool)
        assert isinstance(confidence, float)
    
    def test_is_valid_relationship_invalid_type(self, domain_filter):
        """Test is_valid_relationship with invalid relationship type."""
        is_valid, confidence = domain_filter.is_valid_relationship(
            "Entity A",
            "Entity B",
            "INVALID_TYPE",
            "KnowledgePoint",
            "KnowledgePoint"
        )
        assert is_valid is False
    
    def test_filter_entities_mixed(self, domain_filter):
        """Test filter_entities with mixed entity list."""
        entities = [
            {"name": "Factory Pattern", "type": "KnowledgePoint"},
            {"name": "Random Weather", "type": "KnowledgePoint"},
            {"name": "test_document.pdf", "type": "Document"},
        ]
        filtered = domain_filter.filter_entities(entities)
        assert len(filtered) > 0
        # Document type should always be included
        assert any(e["type"] == "Document" for e in filtered)
    
    def test_filter_relationships_valid(self, domain_filter):
        """Test filter_relationships with valid relationships."""
        relationships = [
            {"type": "BELONGS_TO", "source": "e1", "target": "e2"},
        ]
        entities = {
            "e1": {"name": "Factory Pattern", "type": "KnowledgePoint"},
            "e2": {"name": "Design Pattern", "type": "KnowledgePoint"},
        }
        filtered = domain_filter.filter_relationships(relationships, entities)
        assert isinstance(filtered, list)

