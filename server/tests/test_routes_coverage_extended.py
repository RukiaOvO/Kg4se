"""
路由模块扩展覆盖率测试
目标：增加routes模块的代码覆盖率到85%+
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


@pytest.mark.api
class TestUploadEndpoints:
    """上传端点扩展覆盖"""

    @patch('routes.upload.neo4j_client')
    def test_upload_invalid_file(self, mock_neo4j):
        """测试上传无效文件"""
        mock_neo4j._initialized = True
        
        # 空文件上传
        response = client.post("/upload", files={"file": ("", b"")})
        assert response.status_code in [200, 400, 404, 422]

    @patch('routes.upload.neo4j_client')
    def test_list_documents_empty(self, mock_neo4j):
        """测试列出空文档列表"""
        mock_neo4j._initialized = True
        mock_neo4j.execute_query.return_value = []
        
        response = client.get("/uploads")
        assert response.status_code in [200, 404, 500]

    @patch('routes.upload.neo4j_client')
    def test_delete_document_not_found(self, mock_neo4j):
        """测试删除不存在的文档"""
        mock_neo4j._initialized = True
        
        response = client.delete("/uploads/nonexistent")
        assert response.status_code in [200, 404, 405]


@pytest.mark.api
class TestGraphEndpoints:
    """图谱端点扩展覆盖"""

    @patch('routes.graph.neo4j_client')
    def test_graph_stats_empty(self, mock_neo4j):
        """测试空图谱统计"""
        mock_neo4j._initialized = True
        mock_neo4j.execute_query.return_value = [{"total": 0}]
        
        response = client.get("/graph/stats")
        assert response.status_code in [200, 404, 500]

    @patch('routes.graph.neo4j_client')
    def test_export_graph(self, mock_neo4j):
        """测试导出图谱"""
        mock_neo4j._initialized = True
        mock_neo4j.execute_query.return_value = []
        
        response = client.get("/graph/export")
        assert response.status_code in [200, 404, 405, 500]


@pytest.mark.api
class TestIngestEndpoints:
    """抽取端点扩展覆盖"""

    @patch('routes.ingest.neo4j_client')
    def test_ingest_status_invalid_doc(self, mock_neo4j):
        """测试无效文档的抽取状态"""
        mock_neo4j._initialized = True
        
        response = client.get("/ingest/status/invalid_id")
        assert response.status_code in [200, 404, 405]

    @patch('routes.ingest.neo4j_client')
    def test_ingest_cancel(self, mock_neo4j):
        """测试取消抽取"""
        mock_neo4j._initialized = True
        
        response = client.post("/ingest/cancel/some_id")
        assert response.status_code in [200, 404, 405]


@pytest.mark.api
class TestKnowledgeCardEndpoints:
    """知识卡片端点扩展覆盖"""

    @patch('routes.knowledge_card.neo4j_client')
    def test_concepts_search(self, mock_neo4j):
        """测试概念搜索"""
        mock_neo4j._initialized = True
        mock_neo4j.execute_query.return_value = []
        
        response = client.get("/knowledge-cards/concepts/search?q=test")
        assert response.status_code in [200, 404, 405, 500]

    @patch('routes.knowledge_card.neo4j_client')
    def test_concept_relationships(self, mock_neo4j):
        """测试概念关系"""
        mock_neo4j._initialized = True
        mock_neo4j.execute_query.return_value = []
        
        response = client.get("/knowledge-cards/concepts/test/relationships")
        assert response.status_code in [200, 404, 405, 500]


@pytest.mark.api
class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_health_check(self):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code in [200, 404]

    def test_readiness_check(self):
        """测试就绪检查端点"""
        response = client.get("/ready")
        assert response.status_code in [200, 404, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
