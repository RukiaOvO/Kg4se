# Services 业务服务层

Kg4se 后端业务逻辑服务模块,提供文档处理、知识抽取、图谱操作等核心功能。

## 📦 服务模块

### 1. **parser.py** - 文档解析服务

解析多种格式的文档文件，支持多模态内容提取。

**支持格式**: PDF, TXT, DOCX, MD, 扫描件PDF(OCR)

**核心类**:
```python
from services.parser import ParserFactory

# 使用工厂模式创建解析器
parser = ParserFactory.create_parser("pdf")  # 支持 "pdf", "txt", "word", "md"

# 解析文档
text = parser.parse("document.pdf")
```

**功能**:
- PDF 文本提取（Docling优先，PyMuPDF回退）
- 扫描件PDF OCR识别（集成RapidOCR本地引擎）
- Word 文档解析
- Markdown 解析
- 元数据提取(作者、创建日期等)
- 表格、图表、公式提取（Docling支持）

**解析策略**:
| 文档类型 | 首选方案 | 回退方案 |
|----------|----------|----------|
| 可复制PDF | Docling | PyMuPDF |
| 扫描件PDF | RapidOCR | - |
| DOCX | python-docx | - |
| TXT/MD | 直接读取 | - |

**OCR配置**:
RapidOCR为本地OCR引擎，无需API密钥配置，安装依赖后自动启用。

---

### 2. **extractor.py** - 知识抽取服务

从文本中提取结构化知识。

**核心类**:
```python
from services.extractor import TripletExtractor

extractor = TripletExtractor()
triplets = await extractor.extract(chunk)
```

**功能**:
- 实体识别(NER)
- 关系抽取
- 三元组生成
- 置信度评分

---

### 3. **linker.py** - 实体链接服务

将提取的实体链接到知识库。

**核心类**:
```python
from services.linker import EntityLinker

linker = EntityLinker()
linked_triplets = linker.link_and_merge(triplets)
```

**功能**:
- 实体消歧
- 相似度匹配
- 别名识别
- 新实体创建

---

### 4. **ai_segmenter.py** - AI 分段服务

智能文档分块。

**核心类**:
```python
from services.ai_segmenter import AISegmenter

segmenter = AISegmenter()
# AI分段器自动初始化客户端，支持降级到mock模式
```

**分块策略**:
- `semantic`: 语义边界分块
- `fixed`: 固定大小分块
- `paragraph`: 段落分块
- `sentence`: 句子分块

---

### 5. **qa_service.py** - 问答服务

基于知识图谱的问答系统。

**核心类**:
```python
from services.qa_service import QAService

qa = QAService()
answer = await qa.query_knowledge_graph(
    question="什么是软件工程?",
    context_docs=relevant_docs
)
```

**功能**:
- 问题理解
- 上下文检索
- 答案生成
- 来源追溯

---

### 6. **config_service.py** - 配置管理服务

管理系统配置。

**核心类**:
```python
from services.config_service import ConfigService

config = ConfigService()
settings = config.get_settings()
config.update_settings({"graphrag.chunk_size": 1024})
```

---

### 7. **graphrag_pipeline_service.py** - GraphRAG 流水线服务

编排完整的GraphRAG处理流水线。

**核心类**:
```python
from services.graphrag_pipeline_service import GraphRAGPipelineService

pipeline = GraphRAGPipelineService()
result = await pipeline.process_document(
    document_id="doc_001",
    stages=[1, 2, 3, 4, 5, 6, 7]
)
```

## 🔗 服务依赖关系

```
ParserFactory → GraphRAGPipelineService
                      ↓
            Stage 0 (可选) → Stage 1 → Stage 2 → Stage 3
                                                     ↓
                                               Stage 4 (谓词治理)
                                                     ↓
                                               Stage 5 (图谱存储)
                                                     ↓
                                               Stage 6 (主题构建)
                                                     ↓
                                          Stage 7 (度量) / Stage 8 (查询,可选)
```

## 💡 使用示例

### 完整文档处理流程

```python
from services.parser import ParserFactory
from services.graphrag_pipeline_service import GraphRAGPipelineService

# 1. 解析文档
parser = ParserFactory.create_parser("pdf")
text = parser.parse("document.pdf")

# 2. 启动GraphRAG流水线（异步处理）
pipeline = GraphRAGPipelineService()
result = await pipeline.process_document(
    document_id="doc_001",
    stages=[1, 2, 3, 4, 5, 6, 7]
)

print(f"块数: {result.chunks_count}")
print(f"论断数: {result.claims_count}")
print(f"概念数: {result.concepts_count}")
```

### 智能问答

```python
from services.qa_service import QAService

qa = QAService()

answer = await qa.query_knowledge_graph(
    question="软件工程包含哪些阶段?"
)

print(f"答案: {answer}")
```

## 🧪 单元测试

```bash
# 运行服务层测试
pytest tests/test_services.py -v

# 测试特定服务
pytest tests/test_services.py::TestParserService
pytest tests/test_services.py::TestExtractorService
```

## 📚 相关文档

- [GraphRAG 模块文档](../graphrag/README.md)
- [API 路由文档](../routes/README.md)
- [测试指南](../tests/TEST_GUIDE.md)
