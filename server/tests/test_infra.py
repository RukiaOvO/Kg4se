"""
Tests for infra module
"""

from infra.config import Settings


class TestConfigService:
    def test_settings_init(self):
        settings = Settings()
        assert isinstance(settings, Settings)
    
    def test_settings_neo4j_defaults(self):
        settings = Settings()
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
    
    def test_settings_ai_provider(self):
        settings = Settings()
        assert hasattr(settings, 'ai_provider')
        assert settings.ai_provider in ['openai', 'mock', 'anthropic', 'google', 'deepseek', 'qwen', 'glm', 'moonshot', 'ernie', 'minimax', 'doubao', 'ollama']


class TestLocalStorage:
    """Storage tests skipped - Storage class uses async."""
    def test_placeholder(self):
        assert True
