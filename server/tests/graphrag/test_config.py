"""
Tests for graphrag.config module
"""

import pytest
from graphrag.config import PredicateConfig, OntologyConfig, ThresholdConfig, ConstraintResult, GovernanceStatus


class TestConstraintResult:
    def test_constraint_result_enum(self):
        assert ConstraintResult.PASS.value == "pass"
        assert ConstraintResult.SOFT_VIOLATION.value == "soft"
        assert ConstraintResult.HARD_VIOLATION.value == "hard"


class TestGovernanceStatus:
    def test_governance_status_enum(self):
        assert GovernanceStatus.ACCEPTED.value == "accepted"
        assert GovernanceStatus.PENDING.value == "pending"
        assert GovernanceStatus.REJECTED.value == "rejected"


class TestPredicateConfig:
    @pytest.fixture
    def predicate_config(self):
        config_dict = {
            "version": "1.0.0",
            "standard": ["IS_A", "PART_OF", "SUPPORTS", "USES"],
            "mappings": {
                "is_a": "IS_A",
                "part_of": "PART_OF",
                "supports": "SUPPORTS",
                "uses": "USES"
            },
            "type_constraints": [
                {"source": "Concept", "predicate": "IS_A", "target": ["Concept"]},
                {"source": "Method", "predicate": "IMPLEMENTS", "target": "Tool"},
            ],
            "unmatched_strategy": {"default": "soft"}
        }
        return PredicateConfig(config_dict)
    
    def test_predicate_config_init(self, predicate_config):
        assert predicate_config.version == "1.0.0"
        assert len(predicate_config.standard) == 4
        assert len(predicate_config.mappings) == 4
    
    def test_is_standard_predicate(self, predicate_config):
        assert predicate_config.is_standard_predicate("IS_A") is True
        assert predicate_config.is_standard_predicate("SUPPORTS") is True
        assert predicate_config.is_standard_predicate("UNKNOWN") is False
    
    def test_normalize_predicate(self, predicate_config):
        assert predicate_config.normalize_predicate("is_a") == "IS_A"
        assert predicate_config.normalize_predicate("part_of") == "PART_OF"
        assert predicate_config.normalize_predicate("unknown") is None
    
    def test_validate_type_constraint_pass(self, predicate_config):
        result = predicate_config.validate_type_constraint("Concept", "IS_A", "Concept")
        assert result == ConstraintResult.PASS
    
    def test_validate_type_constraint_hard_violation(self, predicate_config):
        result = predicate_config.validate_type_constraint("Method", "IS_A", "Dataset")
        assert result == ConstraintResult.HARD_VIOLATION
    
    def test_validate_type_constraint_soft_violation(self, predicate_config):
        result = predicate_config.validate_type_constraint("Tool", "UNKNOWN_PREDICATE", "Concept")
        assert result == ConstraintResult.SOFT_VIOLATION
    
    def test_validate_type_constraint_soft_violation_cross_domain(self, predicate_config):
        result = predicate_config.validate_type_constraint("Claim", "IS_A", "Method")
        assert result == ConstraintResult.SOFT_VIOLATION
    
    def test_predicate_config_empty(self):
        config_dict = {}
        config = PredicateConfig(config_dict)
        assert config.version == "1.0.0"
        assert config.standard == []
        assert config.mappings == {}


class TestOntologyConfig:
    @pytest.fixture
    def ontology_config(self):
        config_dict = {
            "version": "2.0.0",
            "node_types": {
                "Concept": {
                    "required_properties": ["name", "description"],
                    "optional_properties": ["confidence"]
                },
                "Claim": {
                    "required_properties": ["text", "evidence_span"],
                    "optional_properties": ["confidence"]
                }
            },
            "relationship_types": {
                "IS_A": {"label": "is_a_relation"},
                "RELATED_TO": {"label": "related_to_relation"}
            },
            "domain_constraints": {
                "allowed_domains": ["NLP", "ML", "NLG"]
            },
            "quality_constraints": {
                "min_confidence": 0.5
            }
        }
        return OntologyConfig(config_dict)
    
    def test_ontology_config_init(self, ontology_config):
        assert ontology_config.version == "2.0.0"
        assert "Concept" in ontology_config.node_types
        assert "Claim" in ontology_config.node_types
    
    def test_get_node_type_schema(self, ontology_config):
        schema = ontology_config.get_node_type_schema("Concept")
        assert schema is not None
        assert "required_properties" in schema
    
    def test_get_node_type_schema_unknown(self, ontology_config):
        schema = ontology_config.get_node_type_schema("Unknown")
        assert schema is None
    
    def test_get_required_properties(self, ontology_config):
        props = ontology_config.get_required_properties("Concept")
        assert "name" in props
        assert "description" in props
        assert "confidence" not in props
    
    def test_get_required_properties_unknown_type(self, ontology_config):
        props = ontology_config.get_required_properties("Unknown")
        assert props == []
    
    def test_validate_node_success(self, ontology_config):
        properties = {"name": "TestConcept", "description": "A test concept"}
        is_valid, errors = ontology_config.validate_node("Concept", properties)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_node_missing_property(self, ontology_config):
        properties = {"name": "TestConcept"}
        is_valid, errors = ontology_config.validate_node("Concept", properties)
        assert is_valid is False
        assert len(errors) == 1
        assert "description" in errors[0]
    
    def test_validate_node_unknown_type(self, ontology_config):
        properties = {"name": "Test"}
        is_valid, errors = ontology_config.validate_node("Unknown", properties)
        assert is_valid is False
        assert "Unknown node type" in errors[0]
    
    def test_get_allowed_domains(self, ontology_config):
        domains = ontology_config.get_allowed_domains()
        assert "NLP" in domains
        assert "ML" in domains
        assert "NLG" in domains
    
    def test_ontology_config_empty(self):
        config = OntologyConfig({})
        assert config.version == "1.0.0"
        assert config.node_types == {}
        assert config.get_allowed_domains() == []


class TestThresholdConfig:
    def test_threshold_config_init(self):
        config_dict = {
            "entity_linking": {"confidence_threshold": 0.7},
            "claim_extraction": {"min_length": 20},
            "theme_building": {"min_community_size": 3},
            "query": {"max_hops": 5}
        }
        config = ThresholdConfig(config_dict)
        
        assert config.entity_linking == {"confidence_threshold": 0.7}
        assert config.claim_extraction == {"min_length": 20}
        assert config.theme_building == {"min_community_size": 3}
        assert config.query == {"max_hops": 5}
    
    def test_threshold_config_empty(self):
        config = ThresholdConfig({})
        assert config.entity_linking == {}
        assert config.claim_extraction == {}
        assert config.theme_building == {}
        assert config.predicate_governance == {}
        assert config.query == {}
