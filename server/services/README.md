# Services 业务服务层

POW_SE 后端业务逻辑服务模块,提供文档处理、知识抽取、图谱操作等核心功能。

## 📦 服务模块

### 1. **parser.py** - 文档解析服务

解析多种格式的文档文件。

**支持格式**: PDF, TXT, DOCX, MD

**核心类**:
```python
from services.parser import DocumentParser

parser = DocumentParser()
text = parser.parse_file("document.pdf")
metadata = parser.extract_metadata("document.pdf")
```

**功能**:
- PDF 文本提取(包含 OCR)
- Word 文档解析
- Markdown 解析
- 元数据提取(作者、创建日期等)

---

### 2. **extractor.py** - 知识抽取服务

从文本中提取结构化知识。

**核心类**:
```python
from services.extractor import KnowledgeExtractor

extractor = KnowledgeExtractor()
entities = await extractor.extract_entities(text)
relationships = await extractor.extract_relationships(text)
```

**功能**:
- 实体识别(NER)
- 关系抽取
- 三元组生成
- 置信度评分

---

### 3. **graph_service.py** - 图谱服务

操作 Neo4j 知识图谱。

**核心类**:
```python
from services.graph_service import GraphService

graph = GraphService(neo4j_client)
node_id = graph.create_node("Concept", {"name": "软件工程"})
graph.create_relationship(node1_id, node2_id, "CONTAINS")
neighbors = graph.get_neighbors(node_id, depth=2)
```

**功能**:
- 节点 CRUD
- 关系 CRUD
- 图遍历查询
- 批量操作
- 事务管理

---

### 4. **linker.py** - 实体链接服务

将提取的实体链接到知识库。

**核心类**:
```python
from services.linker import EntityLinker

linker = EntityLinker()
linked_entities = linker.link_entities(entities, knowledge_base)
```

**功能**:
- 实体消歧
- 相似度匹配
- 别名识别
- 新实体创建

---

### 5. **ai_segmenter.py** - AI 分段服务

智能文档分块。

**核心类**:
```python
from services.ai_segmenter import AISegmenter

segmenter = AISegmenter()
chunks = segmenter.segment(
    document_text,
    chunk_size=512,
    overlap=50,
    strategy="semantic"
)
```

**分块策略**:
- `semantic`: 语义边界分块
- `fixed`: 固定大小分块
- `paragraph`: 段落分块
- `sentence`: 句子分块

---

### 6. **qa_service.py** - 问答服务

基于知识图谱的问答系统。

**核心类**:
```python
from services.qa_service import QAService

qa = QAService()
answer = await qa.answer(
    question="什么是软件工程?",
    context_docs=relevant_docs,
    use_graph=True
)
```

**功能**:
- 问题理解
- 上下文检索
- 答案生成
- 来源追溯

---

### 7. **config_service.py** - 配置管理服务

管理系统配置。

**核心类**:
```python
from services.config_service import ConfigService

config = ConfigService()
chunk_size = config.get("graphrag.chunk_size", default=512)
config.update("graphrag.chunk_size", 1024)
```

## 🔗 服务依赖关系

```
DocumentParser
    ↓
AISegmenter
    ↓
KnowledgeExtractor
    ↓
EntityLinker
    ↓
GraphService
    ↓
QAService
```

## 💡 使用示例

### 完整文档处理流程

```python
from services.parser import DocumentParser
from services.ai_segmenter import AISegmenter
from services.extractor import KnowledgeExtractor
from services.linker import EntityLinker
from services.graph_service import GraphService

# 1. 解析文档
parser = DocumentParser()
text = parser.parse_file("document.pdf")
metadata = parser.extract_metadata("document.pdf")

# 2. 智能分块
segmenter = AISegmenter()
chunks = segmenter.segment(text, chunk_size=512)

# 3. 知识抽取
extractor = KnowledgeExtractor()
entities = await extractor.extract_entities(text)
relationships = await extractor.extract_relationships(text)

# 4. 实体链接
linker = EntityLinker()
linked_entities = linker.link_entities(entities)

# 5. 存储到图谱
graph = GraphService(neo4j_client)
for entity in linked_entities:
    graph.create_node("Concept", entity)

for rel in relationships:
    graph.create_relationship(
        rel["source"],
        rel["target"],
        rel["type"]
    )
```

### 智能问答

```python
from services.qa_service import QAService

qa = QAService()

# 提问
answer = await qa.answer(
    question="软件工程包含哪些阶段?",
    context_limit=5,
    use_graphrag=True
)

print(f"答案: {answer['answer']}")
print(f"置信度: {answer['confidence']}")
print(f"来源: {answer['sources']}")
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
