"""
服务层单元测试
测试业务逻辑和服务功能
"""
import pytest


@pytest.mark.unit
@pytest.mark.service
class TestParserService:
    """文档解析服务测试"""
    
    def test_parse_pdf(self):
        """测试 PDF 解析"""
        from services.parser import ParserFactory
        
        parser = ParserFactory.create_parser("pdf")
        assert parser is not None
    
    def test_parse_txt(self):
        """测试文本文件解析"""
        from services.parser import ParserFactory
        
        parser = ParserFactory.create_parser("txt")
        assert parser is not None


@pytest.mark.unit
@pytest.mark.service
class TestQAService:
    """问答服务测试"""
    
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_answer_question(self):
        """测试回答问题"""
        from services.qa_service import QAService
        
        service = QAService()
        assert service is not None
        assert hasattr(service, 'ai_client')
        assert hasattr(service, 'query_knowledge_graph')


@pytest.mark.unit
@pytest.mark.service
class TestGraphRAGPipelineService:
    """GraphRAG Pipeline 服务测试"""
    
    def test_pipeline_service_init(self):
        """测试 Pipeline 服务初始化"""
        from services.graphrag_pipeline_service import graphrag_pipeline_service
        
        assert graphrag_pipeline_service is not None
        assert hasattr(graphrag_pipeline_service, 'is_available')
        assert hasattr(graphrag_pipeline_service, 'process_document_sync')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "unit"])
