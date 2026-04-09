# Models 模块说明文档

## 📋 模块概述

`models/` 模块定义了项目中所有的数据模型，使用Pydantic进行数据验证和序列化。

**核心职责**:
- 定义API请求/响应模型
- 数据验证和类型检查
- 数据库实体模型
- 配置模型

---

## 📁 模块结构

```
models/
├── __init__.py              # 模块初始化，导出所有模型
├── document.py              # 文档相关模型
├── api.py                   # API通用响应模型
└── settings.py              # 系统设置模型
```

---

## 📄 Document Models (`document.py`)

### 核心模型

#### 1. `DocumentCreate`
文档创建请求模型

```python
class DocumentCreate(BaseModel):
    """文档创建请求"""
    filename: str                          # 文件名
    checksum: str                          # SHA256校验和
    kind: str                              # 文档类型: pdf/md/docx/epub/html
    mime: Optional[str] = None            # MIME类型
    size: int                              # 文件大小（字节）
    source_id: Optional[str] = None       # 来源ID
    meta: Optional[Dict[str, Any]] = None # 元数据
```

**使用示例**:
```python
doc_create = DocumentCreate(
    filename="软件工程.pdf",
    checksum="a1b2c3...",
    kind="pdf",
    mime="application/pdf",
    size=1024000,
    meta={"author": "张三", "pages": 120}
)
```

---

#### 2. `Document`
完整的文档模型（包含数据库字段）

```python
class Document(BaseModel):
    """完整文档模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str                                # 文档ID
    filename: str                          # 文件名
    checksum: str                          # 校验和
    kind: str                              # 文档类型
    mime: Optional[str] = None            # MIME类型
    size: int                              # 文件大小
    path: Optional[str] = None            # 存储路径
    source_id: Optional[str] = None       # 来源ID
    meta: Optional[Dict[str, Any]] = None # 元数据
    created_at: datetime                   # 创建时间
    updated_at: datetime                   # 更新时间
```

**使用场景**:
- API返回文档详情
- 数据库查询结果映射
- Neo4j节点属性转换

---

#### 3. `Chunk`
文本块模型（文档切分后的片段）

```python
class Chunk(BaseModel):
    """文本块模型"""
    doc_id: str                           # 所属文档ID
    chunk_id: str                         # 块ID
    text: str                             # 文本内容
    meta: Dict[str, Any] = Field(         # 元数据
        default_factory=dict,
        description="页码、章节、偏移量等"
    )
```

**元数据示例**:
```python
chunk = Chunk(
    doc_id="doc_001",
    chunk_id="chunk_001",
    text="软件工程是一门研究...",
    meta={
        "page": 5,
        "section": "第二章",
        "offset": 1024,
        "length": 2000,
        "overlap_prev": 200,  # 与前一块重叠字符数
        "overlap_next": 200   # 与后一块重叠字符数
    }
)
```

---

#### 4. `Triplet`
三元组模型（知识图谱的基本单元）

```python
class Triplet(BaseModel):
    """三元组：主语-谓语-宾语"""
    subject: str                          # 主语（头实体）
    predicate: str                        # 谓语（关系）
    object: str                           # 宾语（尾实体）
    confidence: float = Field(            # 置信度
        ge=0.0, le=1.0, default=1.0
    )
    evidence: Dict[str, Any] = Field(     # 证据信息
        default_factory=dict,
        description="文档、块、页码等"
    )
    doc_id: Optional[str] = None         # 来源文档ID
    chunk_id: Optional[str] = None       # 来源块ID
    context: Optional[str] = Field(       # 上下文信息
        None,
        description="关系的上下文描述"
    )
```

**使用示例**:
```python
triplet = Triplet(
    subject="需求分析",
    predicate="is_part_of",
    object="软件工程",
    confidence=0.95,
    doc_id="doc_001",
    chunk_id="chunk_005",
    context="需求分析是软件工程的第一个阶段",
    evidence={
        "page": 12,
        "section": "2.1 软件开发过程",
        "sentence": "需求分析是软件工程的重要组成部分"
    }
)
```

**谓语（关系）类型示例**:
- `is_part_of`: A是B的一部分
- `is_a`: A是B的一种
- `has_property`: A具有属性B
- `related_to`: A与B相关
- `precedes`: A先于B
- `causes`: A导致B
- `used_for`: A用于B

---

#### 5. `AIExtractionRequest`
AI提取配置请求模型

```python
class AIExtractionRequest(BaseModel):
    """AI智能提取配置"""
    enable_ai_segmentation: bool = Field(
        False,
        description="启用AI智能分段"
    )
    user_prompt: Optional[str] = Field(
        None,
        description="用户自定义分析提示词"
    )
    optimize_prompt: bool = Field(
        True,
        description="是否AI优化提示词"
    )
```

**使用场景**:
```python
# 普通分段
config = AIExtractionRequest(
    enable_ai_segmentation=False
)

# AI智能分段 + 自定义Prompt
config = AIExtractionRequest(
    enable_ai_segmentation=True,
    user_prompt="请重点关注软件架构设计相关的知识",
    optimize_prompt=True
)
```

---

## 🔧 API Models (`api.py`)

### 通用响应模型

#### `APIResponse`
标准API响应格式

```python
class APIResponse(BaseModel):
    """标准API响应"""
    success: bool                         # 是否成功
    message: str                          # 消息
    data: Optional[Any] = None           # 响应数据
    error: Optional[str] = None          # 错误信息
    
class PaginatedResponse(BaseModel):
    """分页响应"""
    items: List[Any]                     # 数据列表
    total: int                           # 总数
    page: int                            # 当前页
    page_size: int                       # 每页大小
    pages: int                           # 总页数
```

**使用示例**:
```python
from models.api import APIResponse

# 成功响应
return APIResponse(
    success=True,
    message="文档上传成功",
    data={"doc_id": "doc_001"}
)

# 错误响应
return APIResponse(
    success=False,
    message="文档上传失败",
    error="文件格式不支持"
)

# 分页响应
return PaginatedResponse(
    items=[doc1, doc2, doc3],
    total=100,
    page=1,
    page_size=10,
    pages=10
)
```

---

## ⚙️ Settings Models (`settings.py`)

### 系统设置模型

```python
class AIProviderSettings(BaseModel):
    """AI提供商设置"""
    provider: str                        # 提供商标识
    api_key: str                         # API密钥
    model: str                           # 模型名称
    base_url: Optional[str] = None      # 基础URL
    temperature: float = 0.3            # 温度参数
    max_tokens: int = 4096              # 最大令牌数

class ProcessingSettings(BaseModel):
    """文档处理设置"""
    chunk_size: int = 2000              # 块大小
    chunk_overlap: int = 200            # 块重叠
    enable_coref: bool = True           # 启用指代消解
    enable_entity_linking: bool = True  # 启用实体链接
    extraction_mode: str = "auto"       # 提取模式: auto/rule/llm

class SystemSettings(BaseModel):
    """系统设置"""
    ai_provider: AIProviderSettings     # AI设置
    processing: ProcessingSettings      # 处理设置
    neo4j_uri: str                      # Neo4j URI
    redis_host: str                     # Redis主机
```

---

## 🎯 使用模式

### 1. API请求验证

```python
from fastapi import APIRouter, HTTPException
from models.document import DocumentCreate, AIExtractionRequest

router = APIRouter()

@router.post("/documents")
async def create_document(
    doc: DocumentCreate,
    ai_config: AIExtractionRequest = AIExtractionRequest()
):
    """创建文档"""
    # Pydantic自动验证数据
    if doc.size > 100 * 1024 * 1024:
        raise HTTPException(400, "文件过大")
    
    # 处理逻辑...
    return {"doc_id": "doc_001"}
```

### 2. 数据库映射

```python
from models.document import Document

# Neo4j查询结果转模型
def get_document(doc_id: str) -> Document:
    result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $id}) RETURN d",
        {"id": doc_id}
    )
    # 自动转换
    return Document(**result[0]["d"])
```

### 3. 序列化

```python
# 模型转JSON
doc = Document(...)
json_str = doc.model_dump_json()

# JSON转模型
doc = Document.model_validate_json(json_str)

# 模型转字典
doc_dict = doc.model_dump()
```

### 4. 验证和转换

```python
from pydantic import ValidationError

try:
    doc = DocumentCreate(
        filename="test.pdf",
        checksum="abc",
        kind="unknown",  # 无效类型
        size=-100        # 负数
    )
except ValidationError as e:
    print(e.json())
```

---

## 📐 数据验证规则

### 字段验证

```python
from pydantic import Field, field_validator

class Triplet(BaseModel):
    confidence: float = Field(
        ge=0.0,      # 大于等于0
        le=1.0,      # 小于等于1
        default=1.0
    )
    
    @field_validator('subject', 'object')
    @classmethod
    def validate_entity(cls, v: str) -> str:
        """验证实体名称"""
        if not v or len(v.strip()) == 0:
            raise ValueError("实体名称不能为空")
        if len(v) > 200:
            raise ValueError("实体名称过长")
        return v.strip()
```

### 模型验证

```python
from pydantic import model_validator

class AIExtractionRequest(BaseModel):
    enable_ai_segmentation: bool
    user_prompt: Optional[str] = None
    
    @model_validator(mode='after')
    def check_prompt_required(self):
        """如果启用AI分段，必须提供提示词"""
        if self.enable_ai_segmentation and not self.user_prompt:
            raise ValueError("启用AI分段时必须提供user_prompt")
        return self
```

---

## 🔄 模型转换

### Neo4j ↔ Pydantic

```python
from datetime import datetime

# Neo4j节点 → Pydantic模型
def node_to_model(node) -> Document:
    return Document(
        id=node["id"],
        filename=node["filename"],
        checksum=node["checksum"],
        kind=node["kind"],
        size=node["size"],
        created_at=datetime.fromisoformat(node["created_at"]),
        updated_at=datetime.fromisoformat(node["updated_at"])
    )

# Pydantic模型 → Neo4j属性
def model_to_properties(doc: Document) -> Dict:
    return {
        "id": doc.id,
        "filename": doc.filename,
        "checksum": doc.checksum,
        "kind": doc.kind,
        "size": doc.size,
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat()
    }
```

---

## 🎨 最佳实践

### 1. 使用ConfigDict

```python
from pydantic import ConfigDict

class Document(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # 支持ORM模式
        populate_by_name=True, # 支持字段别名
        str_strip_whitespace=True,  # 自动去除空格
        validate_assignment=True  # 赋值时也验证
    )
```

### 2. 可选字段处理

```python
from typing import Optional

class Document(BaseModel):
    # 必填字段
    filename: str
    
    # 可选字段，默认None
    meta: Optional[Dict[str, Any]] = None
    
    # 可选字段，有默认值
    kind: str = "pdf"
```

### 3. 字段别名

```python
from pydantic import Field

class Document(BaseModel):
    doc_id: str = Field(alias="id")
    file_name: str = Field(alias="filename")
    
    # 序列化时使用别名
    model_config = ConfigDict(populate_by_name=True)
```

### 4. 复杂验证

```python
from pydantic import field_validator

class Chunk(BaseModel):
    text: str
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("文本块太短")
        if len(v) > 10000:
            raise ValueError("文本块太长")
        return v
```

---

## 📊 性能优化

### 1. 延迟验证

```python
# 创建模型时验证（默认）
doc = Document(**data)

# 跳过验证（危险！仅用于可信数据）
doc = Document.model_construct(**data)
```

### 2. 批量处理

```python
# 不推荐：逐个验证
docs = [Document(**d) for d in data_list]

# 推荐：使用model_validate
from pydantic import TypeAdapter

adapter = TypeAdapter(List[Document])
docs = adapter.validate_python(data_list)
```

### 3. 部分更新

```python
# 只更新部分字段
doc = Document(...)
updates = {"filename": "new_name.pdf"}
updated_doc = doc.model_copy(update=updates)
```

---

## 🧪 测试支持

### Fixture示例

```python
# tests/conftest.py
import pytest
from models.document import Document, Chunk, Triplet

@pytest.fixture
def sample_document():
    return Document(
        id="doc_001",
        filename="test.pdf",
        checksum="abc123",
        kind="pdf",
        size=1024,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@pytest.fixture
def sample_triplet():
    return Triplet(
        subject="Python",
        predicate="is_a",
        object="编程语言",
        confidence=1.0,
        doc_id="doc_001",
        chunk_id="chunk_001"
    )
```

---

## 📚 依赖项

```
pydantic>=2.0.0         # 核心依赖
pydantic-settings>=2.0  # 配置管理
```

---

## 🔗 相关文档

- [Infra模块说明](../infra/README.md)
- [Services模块说明](../services/README.md)
- [API文档](../routes/README.md)

---

*最后更新: 2025-01-XX*
