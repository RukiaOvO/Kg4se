# Infra 模块说明文档

## 📋 模块概述

`infra/` 模块提供项目的基础设施服务，包括AI提供商集成、数据库连接、配置管理、队列服务和存储服务。

**核心职责**:
- 统一的AI服务接口（支持10+主流AI提供商）
- Neo4j图数据库连接和操作
- 应用配置管理
- 异步任务队列
- 文件存储服务

---

## 📁 模块结构

```
infra/
├── __init__.py              # 模块初始化
├── ai_providers.py          # AI提供商统一接口 (616行)
├── config.py                # 配置管理 (40行)
├── neo4j_client.py          # Neo4j数据库客户端 (594行)
├── queue.py                 # 异步任务队列 (210行)
├── storage.py               # 文件存储服务 (55行)
└── schema.cypher            # Neo4j数据库Schema定义
```

---

## 🤖 AI Providers (`ai_providers.py`)

### 功能说明

提供统一的AI服务接口，支持多个主流AI提供商的无缝切换。

### 支持的AI提供商

| 提供商 | 标识符 | 代表模型 | 备注 |
|--------|--------|----------|------|
| OpenAI | `openai` | GPT-4, GPT-3.5 | 官方API |
| Anthropic | `anthropic` | Claude 3 | 官方API |
| Google | `google` | Gemini Pro | Google AI |
| DeepSeek | `deepseek` | DeepSeek-V2 | 国产大模型 |
| 通义千问 | `qwen` | Qwen-Plus, Qwen-Max | 阿里云 |
| 智谱AI | `glm` | GLM-4 | 清华系 |
| Moonshot | `moonshot` | Moonshot-v1 | 月之暗面 Kimi |
| 文心一言 | `ernie` | ERNIE-Bot | 百度 |
| MiniMax | `minimax` | abab6-chat | MiniMax |
| 豆包 | `doubao` | Doubao-pro | 字节跳动 |
| Ollama | `ollama` | 本地模型 | 本地部署 |
| Mock | `mock` | 测试模式 | 用于测试 |

### 核心类

#### `BaseAIClient`
抽象基类，定义统一的AI客户端接口。

```python
class BaseAIClient:
    def __init__(self, model: str, **kwargs):
        """初始化AI客户端"""
        
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        """发送对话请求，返回文本响应"""
```

#### `AIProviderFactory`
工厂类，负责创建和管理AI客户端实例。

```python
class AIProviderFactory:
    @staticmethod
    def create_client(
        provider: AIProviderType,
        api_key: str,
        model: str,
        base_url: Optional[str] = None
    ) -> BaseAIClient:
        """创建AI客户端实例"""
        
    @staticmethod
    def get_provider_info(provider: str) -> Dict[str, Any]:
        """获取提供商信息（名称、默认模型等）"""
```

### 使用示例

```python
from infra.ai_providers import AIProviderFactory

# 创建OpenAI客户端
client = AIProviderFactory.create_client(
    provider="openai",
    api_key="sk-xxx",
    model="gpt-4"
)

# 发送对话请求
response = client.chat_completion(
    messages=[
        {"role": "system", "content": "你是一个专业的助手"},
        {"role": "user", "content": "什么是知识图谱？"}
    ],
    temperature=0.7
)
print(response)

# 使用国产模型（通义千问）
qwen_client = AIProviderFactory.create_client(
    provider="qwen",
    api_key="sk-xxx",
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# Mock模式（测试用）
mock_client = AIProviderFactory.create_client(
    provider="mock",
    api_key="mock",
    model="mock"
)
```

### 扩展新提供商

1. 继承 `BaseAIClient` 类
2. 实现 `chat_completion` 方法
3. 在 `AIProviderFactory.create_client()` 中注册
4. 更新 `AIProviderType` 类型定义

```python
class NewProviderClient(BaseAIClient):
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        # 初始化提供商SDK
        
    def chat_completion(self, messages, temperature=0.3, **extra_params) -> str:
        # 实现具体的API调用逻辑
        pass
```

---

## 🗄️ Neo4j Client (`neo4j_client.py`)

### 功能说明

提供Neo4j图数据库的连接管理和常用操作封装。

### 核心特性

- ✅ 自动重连机制（最多30次重试）
- ✅ Schema自动初始化
- ✅ 批量操作支持
- ✅ 类型转换（Pydantic ↔ Neo4j）
- ✅ 查询结果封装

### 主要方法

```python
class Neo4jClient:
    def initialize(self):
        """初始化连接和Schema（显式调用）"""
        
    def execute_query(self, query: str, params: Dict = None) -> List[Dict]:
        """执行Cypher查询"""
        
    def create_document(self, doc: Document) -> Dict:
        """创建文档节点"""
        
    def create_chunk(self, chunk: Chunk) -> Dict:
        """创建文本块节点"""
        
    def create_concept(self, name: str, meta: Dict = None) -> Dict:
        """创建概念节点"""
        
    def create_triplet(self, triplet: Triplet) -> Dict:
        """创建三元组关系"""
        
    def find_concept_by_name(self, name: str) -> Optional[Dict]:
        """根据名称查找概念"""
        
    def get_concept_neighbors(
        self,
        concept_id: str,
        depth: int = 1,
        limit: int = 50
    ) -> List[Dict]:
        """获取概念的邻居节点"""
        
    def bulk_create_nodes(
        self,
        label: str,
        nodes: List[Dict],
        batch_size: int = 1000
    ):
        """批量创建节点"""
```

### 使用示例

```python
from infra.neo4j_client import neo4j_client
from models.document import Document, Chunk, Triplet

# 1. 初始化连接
neo4j_client.initialize()

# 2. 创建文档节点
doc = Document(
    id="doc_001",
    filename="软件工程.pdf",
    checksum="abc123",
    kind="pdf",
    size=1024000
)
neo4j_client.create_document(doc)

# 3. 创建概念节点
concept = neo4j_client.create_concept(
    name="软件工程",
    meta={"domain": "计算机科学", "type": "学科"}
)

# 4. 创建三元组关系
triplet = Triplet(
    subject="需求分析",
    predicate="is_part_of",
    object="软件工程",
    confidence=0.95,
    doc_id="doc_001",
    chunk_id="chunk_001"
)
neo4j_client.create_triplet(triplet)

# 5. 查询概念
result = neo4j_client.find_concept_by_name("软件工程")
print(result)

# 6. 获取邻居
neighbors = neo4j_client.get_concept_neighbors(
    concept_id="concept_001",
    depth=2,
    limit=100
)
```

### 数据模型

#### 节点类型

- **Document**: 文档节点
  - 属性: `id`, `filename`, `checksum`, `kind`, `size`, `path`, `created_at`
  
- **Chunk**: 文本块节点
  - 属性: `chunk_id`, `text`, `doc_id`, `meta`
  
- **Concept**: 概念节点
  - 属性: `id`, `name`, `canonical_name`, `aliases`, `meta`, `created_at`

#### 关系类型

- **CONTAINS**: Document → Chunk (文档包含文本块)
- **HAS_CHUNK**: Concept → Chunk (概念来源于文本块)
- **RELATES_TO**: Concept → Concept (概念之间的关系)
  - 属性: `predicate`, `confidence`, `evidence`

---

## ⚙️ Config (`config.py`)

### 功能说明

基于Pydantic的配置管理，支持环境变量和.env文件。

### 配置项

```python
class Settings(BaseSettings):
    # 应用配置
    app_name: str = "POW"
    debug: bool = False
    
    # Neo4j配置
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_pass: str = "password"
    
    # AI配置（默认值）
    ai_provider: str = "qwen"
    ai_api_key: str = ""
    ai_model: str = "qwen-plus"
    ai_base_url: Optional[str] = None
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # 存储配置
    upload_dir: str = "uploads"
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
```

### 使用方式

```python
from infra.config import settings

# 读取配置
print(settings.neo4j_uri)
print(settings.ai_provider)

# 配置会自动从环境变量或.env文件加载
# 优先级: 环境变量 > .env文件 > 默认值
```

### 环境变量示例

```bash
# .env文件
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASS=your_password

AI_PROVIDER=qwen
AI_API_KEY=sk-xxx
AI_MODEL=qwen-plus
AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

---

## 📮 Queue (`queue.py`)

### 功能说明

基于Redis的异步任务队列，用于处理长时间运行的任务（如文档处理、知识抽取等）。

### 核心功能

- 任务提交和状态跟踪
- 优先级队列支持
- 任务超时处理
- 重试机制
- 进度回调

### 使用示例

```python
from infra.queue import task_queue
from typing import Dict, Any

# 1. 定义任务处理函数
async def process_document(task_id: str, params: Dict[str, Any]):
    """处理文档任务"""
    doc_id = params["doc_id"]
    # 处理逻辑...
    await task_queue.update_progress(task_id, 50)
    # 继续处理...
    await task_queue.update_progress(task_id, 100)
    return {"status": "success", "doc_id": doc_id}

# 2. 提交任务
task_id = await task_queue.submit_task(
    task_type="document_processing",
    params={"doc_id": "doc_001"},
    priority=1
)

# 3. 查询任务状态
status = await task_queue.get_task_status(task_id)
print(status)  # {"status": "running", "progress": 50}

# 4. 等待任务完成
result = await task_queue.wait_for_task(task_id, timeout=300)
```

---

## 💾 Storage (`storage.py`)

### 功能说明

文件存储服务，处理上传文件的保存、读取和删除。

### 主要方法

```python
class FileStorage:
    def save_file(self, file_data: bytes, filename: str) -> str:
        """保存文件，返回文件路径"""
        
    def read_file(self, file_path: str) -> bytes:
        """读取文件内容"""
        
    def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息（大小、修改时间等）"""
```

### 使用示例

```python
from infra.storage import file_storage

# 保存文件
file_path = file_storage.save_file(
    file_data=uploaded_file.read(),
    filename="document.pdf"
)

# 读取文件
content = file_storage.read_file(file_path)

# 删除文件
file_storage.delete_file(file_path)
```

---

## 🗃️ Schema (`schema.cypher`)

### Neo4j数据库Schema定义

包含所有节点和关系的约束、索引定义。

**主要约束**:
- Document节点的id唯一性
- Concept节点的name唯一性
- Chunk节点的chunk_id唯一性

**索引**:
- Concept.name (全文搜索)
- Concept.canonical_name
- Document.checksum
- Chunk.doc_id

---

## 🔧 最佳实践

### 1. AI提供商选择

```python
# 开发环境：使用Mock模式
if settings.debug:
    client = AIProviderFactory.create_client("mock", "mock", "mock")
else:
    # 生产环境：使用配置的提供商
    client = AIProviderFactory.create_client(
        provider=settings.ai_provider,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        base_url=settings.ai_base_url
    )
```

### 2. Neo4j连接管理

```python
# 应用启动时初始化
@app.on_event("startup")
async def startup_event():
    neo4j_client.initialize()

# 应用关闭时清理
@app.on_event("shutdown")
async def shutdown_event():
    if neo4j_client.driver:
        neo4j_client.driver.close()
```

### 3. 批量操作优化

```python
# 不推荐：逐个创建
for concept in concepts:
    neo4j_client.create_concept(concept["name"], concept["meta"])

# 推荐：批量创建
neo4j_client.bulk_create_nodes(
    label="Concept",
    nodes=concepts,
    batch_size=1000
)
```

### 4. 错误处理

```python
from neo4j.exceptions import ServiceUnavailable

try:
    neo4j_client.initialize()
except ServiceUnavailable:
    logger.error("Neo4j服务不可用，请检查数据库连接")
    # 降级处理或重试
```

---

## 📊 性能考虑

### AI调用优化

- 使用合适的temperature参数（推理任务用0.1-0.3）
- 批量处理减少API调用次数
- 实现缓存机制避免重复调用

### Neo4j查询优化

- 使用索引加速查询
- 限制查询深度和返回数量
- 使用参数化查询防止注入
- 批量操作替代单条插入

### 队列设计

- 合理设置任务优先级
- 实现超时和重试机制
- 监控队列长度避免积压

---

## 🧪 测试支持

### Mock模式

AI提供商的Mock模式用于测试环境：

```python
mock_client = AIProviderFactory.create_client("mock", "mock", "mock")
response = mock_client.chat_completion([...])
# 返回预定义的测试响应
```

### 测试配置

```python
# tests/conftest.py
@pytest.fixture
def test_neo4j_client():
    """测试用Neo4j客户端"""
    client = Neo4jClient()
    # 使用测试数据库
    client.initialize()
    yield client
    # 清理测试数据
```

---

## 📚 依赖项

```
openai>=1.0.0           # OpenAI SDK
anthropic>=0.7.0        # Anthropic SDK
neo4j>=5.14.0           # Neo4j驱动
redis>=5.0.0            # Redis客户端
pydantic>=2.0.0         # 数据验证
pydantic-settings>=2.0  # 配置管理
```

---

## 🔗 相关文档

- [Services模块说明](../services/README.md)
- [GraphRAG模块说明](../graphrag/README.md)
- [Routes模块说明](../routes/README.md)
- [测试文档](../tests/README.md)

---

*最后更新: 2025-01-XX*
