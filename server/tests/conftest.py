"""
Pytest 配置和共享 fixtures
"""
import os
import sys
import pytest
from typing import Generator
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 测试环境配置
os.environ["TESTING"] = "1"
os.environ["NEO4J_URI"] = os.getenv("TEST_NEO4J_URI", "bolt://localhost:7687")
os.environ["NEO4J_USER"] = os.getenv("TEST_NEO4J_USER", "neo4j")
os.environ["NEO4J_PASSWORD"] = os.getenv("TEST_NEO4J_PASSWORD", "password")
os.environ["REDIS_URL"] = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """返回测试数据目录"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_document(test_data_dir: Path) -> str:
    """返回示例文档内容"""
    doc_path = test_data_dir / "test_doc.txt"
    if doc_path.exists():
        return doc_path.read_text(encoding="utf-8")
    return "这是一个测试文档。软件工程是一门关于软件开发的学科。"


@pytest.fixture(scope="function")
def mock_ai_client(monkeypatch):
    """模拟 AI 客户端"""
    class MockAIClient:
        def __init__(self, *args, **kwargs):
            pass
        
        async def chat_completion(self, messages, **kwargs):
            return {
                "choices": [{
                    "message": {
                        "content": "模拟的 AI 响应"
                    }
                }]
            }
        
        def embed(self, text):
            # 返回固定长度的向量
            return [0.1] * 1536
    
    return MockAIClient()


@pytest.fixture(scope="session")
def neo4j_test_client():
    """Neo4j 测试客户端 (需要真实数据库连接)"""
    try:
        from infra.neo4j_client import Neo4jClient
        
        client = Neo4jClient()
        client.initialize()
        
        yield client
        
        # 清理测试数据
        with client.driver.session() as session:
            session.run("MATCH (n:TestNode) DETACH DELETE n")
        
        client.close()
    except Exception as e:
        pytest.skip(f"无法连接到 Neo4j 测试数据库: {e}")


@pytest.fixture(scope="function")
def clean_test_db(neo4j_test_client):
    """每个测试前清理测试节点"""
    with neo4j_test_client.driver.session() as session:
        session.run("MATCH (n:TestNode) DETACH DELETE n")
    yield
    with neo4j_test_client.driver.session() as session:
        session.run("MATCH (n:TestNode) DETACH DELETE n")


@pytest.fixture
def sample_chunks():
    """示例文本块"""
    return [
        {
            "id": "chunk_1",
            "text": "软件工程是一门关于软件开发的学科。",
            "index": 0
        },
        {
            "id": "chunk_2", 
            "text": "它涉及需求分析、设计、实现和测试等阶段。",
            "index": 1
        }
    ]


@pytest.fixture
def sample_claims():
    """示例论断"""
    return [
        {
            "subject": "软件工程",
            "predicate": "是",
            "object": "一门学科",
            "confidence": 0.9
        },
        {
            "subject": "软件工程",
            "predicate": "涉及",
            "object": "需求分析",
            "confidence": 0.85
        }
    ]


@pytest.fixture
def sample_document_metadata():
    """示例文档元数据"""
    return {
        "id": "test_doc_001",
        "filename": "test_document.pdf",
        "size": 1024,
        "checksum": "abc123def456",
        "mime_type": "application/pdf"
    }


@pytest.fixture(scope="function")
def mock_neo4j_client(monkeypatch):
    """Mock Neo4j客户端用于API测试"""
    from unittest.mock import Mock, MagicMock
    
    mock_client = Mock()
    mock_client._initialized = True
    mock_client.execute_query = Mock(return_value=[{"total": 0}])
    mock_client.create_document = Mock(return_value={"id": "doc_123", "filename": "test.txt"})
    
    # Patch neo4j_client实例
    import infra.neo4j_client
    monkeypatch.setattr(infra.neo4j_client, "neo4j_client", mock_client)
    
    return mock_client


# 测试辅助函数
def assert_valid_uuid(value: str) -> bool:
    """验证是否为有效的 UUID"""
    import uuid
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


def assert_valid_iso_datetime(value: str) -> bool:
    """验证是否为有效的 ISO 日期时间格式"""
    from datetime import datetime
    try:
        datetime.fromisoformat(value.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False
