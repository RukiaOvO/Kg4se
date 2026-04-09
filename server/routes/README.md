# API Routes 文档

POW_SE 后端 API 路由模块,提供 RESTful API 接口。

## 📋 目录

- [API 概览](#api-概览)
- [路由模块](#路由模块)
- [请求响应格式](#请求响应格式)
- [错误处理](#错误处理)
- [认证授权](#认证授权)
- [API 示例](#api-示例)

## 🌐 API 概览

### 基础信息

- **Base URL**: `http://localhost:8000`
- **API 文档**: `http://localhost:8000/docs` (Swagger UI)
- **ReDoc**: `http://localhost:8000/redoc`
- **Content-Type**: `application/json`
- **字符编码**: UTF-8

### 路由前缀

| 前缀 | 模块 | 描述 |
|------|------|------|
| `/uploads` | upload.py | 文档上传和管理 |
| `/ingest` | ingest.py | 知识抽取任务 |
| `/graph` | graph.py | 图谱查询和可视化 |
| `/qa` | qa.py | 智能问答 |
| `/knowledge-cards` | knowledge_card.py | 知识卡片管理 |
| `/settings` | settings.py | 系统设置 |

## 📦 路由模块

### 1. Upload Routes (`upload.py`)

**文档上传和管理**

#### `POST /uploads`

上传文档文件

**请求**:
```http
POST /uploads
Content-Type: multipart/form-data

file: <文件数据>
```

**响应**:
```json
{
  "id": "doc_abc123",
  "filename": "软件工程.pdf",
  "size": 1024000,
  "checksum": "sha256_hash",
  "mime_type": "application/pdf",
  "created_at": "2024-01-01T12:00:00Z",
  "status": "uploaded"
}
```

#### `GET /uploads`

获取文档列表

**查询参数**:
- `skip`: int = 0 - 分页偏移
- `limit`: int = 20 - 每页数量
- `sort_by`: str = "created_at" - 排序字段
- `order`: str = "desc" - 排序方向

**响应**:
```json
{
  "documents": [
    {
      "id": "doc_001",
      "filename": "软件工程.pdf",
      "size": 1024000,
      "processing_status": "completed",
      "created_at": "2024-01-01T12:00:00Z",
      "stats": {
        "chunks": 120,
        "concepts": 45,
        "claims": 230
      }
    }
  ],
  "total": 100,
  "page": 1,
  "pages": 5
}
```

#### `GET /uploads/{document_id}`

获取文档详情

**响应**:
```json
{
  "id": "doc_001",
  "filename": "软件工程.pdf",
  "size": 1024000,
  "checksum": "sha256_hash",
  "mime_type": "application/pdf",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T14:30:00Z",
  "processing_status": "completed",
  "metadata": {
    "author": "作者",
    "pages": 200
  },
  "stats": {
    "chunks": 120,
    "concepts": 45,
    "claims": 230,
    "processing_time": 120.5
  }
}
```

#### `DELETE /uploads/{document_id}`

删除文档

**响应**: `204 No Content`

---

### 2. Ingest Routes (`ingest.py`)

**知识抽取任务管理**

#### `POST /ingest/{document_id}`

启动文档知识抽取

**请求体**:
```json
{
  "stages": [0, 1, 2, 3, 4, 5, 6],
  "priority": "normal",
  "options": {
    "chunk_size": 512,
    "overlap": 50
  }
}
```

**响应**:
```json
{
  "task_id": "task_xyz789",
  "document_id": "doc_001",
  "status": "queued",
  "created_at": "2024-01-01T12:00:00Z",
  "estimated_time": 300
}
```

#### `GET /ingest/status/{task_id}`

查询抽取任务状态

**响应**:
```json
{
  "task_id": "task_xyz789",
  "document_id": "doc_001",
  "status": "processing",
  "progress": 45.5,
  "current_stage": 3,
  "stages_completed": [0, 1, 2],
  "started_at": "2024-01-01T12:00:00Z",
  "estimated_completion": "2024-01-01T12:05:00Z",
  "results": {
    "chunks_processed": 50,
    "claims_extracted": 120
  }
}
```

#### `GET /ingest/status`

获取所有任务状态

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "task_1",
      "document_id": "doc_001",
      "status": "completed",
      "progress": 100
    },
    {
      "task_id": "task_2",
      "document_id": "doc_002",
      "status": "processing",
      "progress": 60
    }
  ],
  "summary": {
    "queued": 2,
    "processing": 1,
    "completed": 10,
    "failed": 0
  }
}
```

#### `POST /ingest/{task_id}/cancel`

取消正在进行的任务

**响应**: `200 OK`

---

### 3. Graph Routes (`graph.py`)

**知识图谱查询和可视化**

#### `GET /graph/visualize`

获取图谱可视化数据

**查询参数**:
- `limit`: int = 500 - 最大节点数
- `node_type`: str = None - 筛选节点类型
- `depth`: int = 2 - 关系深度

**响应**:
```json
{
  "nodes": [
    {
      "id": "concept_001",
      "labels": ["Concept"],
      "properties": {
        "name": "软件工程",
        "type": "Discipline",
        "description": "...",
        "created_at": "2024-01-01T12:00:00"
      }
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "source": "concept_001",
      "target": "concept_002",
      "type": "CONTAINS",
      "properties": {
        "weight": 0.95,
        "created_at": "2024-01-01T12:00:00"
      }
    }
  ],
  "stats": {
    "node_count": 100,
    "edge_count": 150
  }
}
```

#### `GET /graph/documents/{document_id}/graph`

获取文档子图

**查询参数**:
- `depth`: int = 2 - 关系深度

**响应**: (同 visualize 格式)

#### `GET /graph/concepts/{concept_name}/graph`

获取概念子图

**查询参数**:
- `depth`: int = 2 - 关系深度

**响应**: (同 visualize 格式)

#### `GET /graph/stats`

获取图谱统计信息

**响应**:
```json
{
  "node_count": 1234,
  "edge_count": 3456,
  "document_count": 50,
  "concept_count": 800,
  "claim_count": 2000,
  "avg_degree": 2.8,
  "density": 0.035,
  "components": 3,
  "largest_component_size": 1200
}
```

#### `POST /graph/nodes`

创建新节点

**请求体**:
```json
{
  "labels": ["Concept"],
  "properties": {
    "name": "新概念",
    "type": "Technology",
    "description": "..."
  }
}
```

#### `PUT /graph/nodes/{node_id}`

更新节点

**请求体**:
```json
{
  "properties": {
    "description": "更新后的描述"
  }
}
```

#### `DELETE /graph/nodes/{node_id}`

删除节点

**响应**: `204 No Content`

---

### 4. QA Routes (`qa.py`)

**智能问答系统**

#### `POST /qa/ask`

提交问题

**请求体**:
```json
{
  "question": "什么是软件工程?",
  "context_limit": 5,
  "use_graphrag": true,
  "session_id": "session_abc"
}
```

**响应**:
```json
{
  "answer": "软件工程是一门关于软件开发的学科...",
  "confidence": 0.92,
  "sources": [
    {
      "type": "chunk",
      "id": "chunk_001",
      "content": "软件工程定义...",
      "document": "软件工程教材.pdf",
      "relevance": 0.95
    }
  ],
  "related_concepts": [
    "需求分析",
    "系统设计",
    "软件测试"
  ],
  "response_time": 1.2
}
```

#### `GET /qa/history`

获取问答历史

**查询参数**:
- `session_id`: str = None - 会话ID
- `limit`: int = 20

**响应**:
```json
{
  "history": [
    {
      "question": "什么是软件工程?",
      "answer": "...",
      "timestamp": "2024-01-01T12:00:00Z",
      "session_id": "session_abc"
    }
  ]
}
```

#### `POST /qa/feedback`

提交答案反馈

**请求体**:
```json
{
  "qa_id": "qa_001",
  "rating": 5,
  "feedback": "回答很准确",
  "helpful": true
}
```

---

### 5. Knowledge Card Routes (`knowledge_card.py`)

**知识卡片管理**

#### `GET /knowledge-cards/concepts`

获取概念列表

**查询参数**:
- `type`: str = None - 概念类型筛选
- `search`: str = None - 搜索关键词
- `skip`: int = 0
- `limit`: int = 50

**响应**:
```json
{
  "concepts": [
    {
      "id": "concept_001",
      "name": "软件工程",
      "type": "Discipline",
      "description": "...",
      "related_count": 15,
      "document_count": 5
    }
  ],
  "total": 800
}
```

#### `GET /knowledge-cards/concepts/{concept_id}`

获取概念详情

**响应**:
```json
{
  "id": "concept_001",
  "name": "软件工程",
  "type": "Discipline",
  "description": "系统化、规范化、可量化的软件开发方法",
  "aliases": ["SE", "Software Engineering"],
  "properties": {
    "definition": "...",
    "examples": ["..."]
  },
  "relationships": [
    {
      "type": "CONTAINS",
      "target": "需求分析",
      "weight": 0.9
    }
  ],
  "documents": [
    {
      "id": "doc_001",
      "filename": "软件工程教材.pdf",
      "mentions": 25
    }
  ],
  "evidence": [
    {
      "chunk_id": "chunk_001",
      "text": "软件工程是...",
      "confidence": 0.95
    }
  ],
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-05T10:30:00Z"
}
```

#### `PUT /knowledge-cards/concepts/{concept_id}`

更新概念

**请求体**:
```json
{
  "description": "更新后的描述",
  "properties": {
    "definition": "新定义"
  }
}
```

#### `POST /knowledge-cards/relationships`

创建概念关系

**请求体**:
```json
{
  "source": "concept_001",
  "target": "concept_002",
  "type": "DEPENDS_ON",
  "properties": {
    "weight": 0.85
  }
}
```

---

### 6. Settings Routes (`settings.py`)

**系统设置**

#### `GET /settings`

获取系统设置

**响应**:
```json
{
  "system": {
    "version": "1.0.0",
    "environment": "production"
  },
  "graphrag": {
    "chunk_size": 512,
    "overlap": 50,
    "min_confidence": 0.7
  },
  "ai": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  },
  "database": {
    "neo4j_uri": "bolt://localhost:7687",
    "neo4j_database": "neo4j"
  }
}
```

#### `PUT /settings`

更新设置

**请求体**:
```json
{
  "graphrag": {
    "chunk_size": 1024
  }
}
```

#### `GET /settings/health`

健康检查

**响应**:
```json
{
  "status": "healthy",
  "services": {
    "neo4j": "connected",
    "redis": "connected",
    "ai": "available"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 📄 请求响应格式

### 统一响应结构

成功响应:
```json
{
  "data": { ... },
  "message": "操作成功",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

错误响应:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数验证失败",
    "details": [
      {
        "field": "limit",
        "message": "必须是正整数"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 分页格式

```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5,
  "has_next": true,
  "has_prev": false
}
```

## ❌ 错误处理

### HTTP 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 204 | No Content | 删除成功 |
| 400 | Bad Request | 参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 409 | Conflict | 资源冲突 |
| 422 | Unprocessable Entity | 数据验证失败 |
| 429 | Too Many Requests | 请求过于频繁 |
| 500 | Internal Server Error | 服务器错误 |
| 503 | Service Unavailable | 服务不可用 |

### 错误代码

| 代码 | 描述 |
|------|------|
| `VALIDATION_ERROR` | 参数验证错误 |
| `NOT_FOUND` | 资源不存在 |
| `ALREADY_EXISTS` | 资源已存在 |
| `PROCESSING_ERROR` | 处理失败 |
| `DATABASE_ERROR` | 数据库错误 |
| `AI_SERVICE_ERROR` | AI 服务错误 |
| `RATE_LIMIT_EXCEEDED` | 超过速率限制 |

## 🔐 认证授权

(待实现)

```http
Authorization: Bearer <access_token>
```

## 💡 API 示例

### Python 客户端示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 上传文档
with open("document.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/uploads",
        files={"file": f}
    )
    doc = response.json()
    print(f"上传成功: {doc['id']}")

# 启动知识抽取
response = requests.post(
    f"{BASE_URL}/ingest/{doc['id']}",
    json={"stages": [0, 1, 2, 3]}
)
task = response.json()

# 查询任务状态
status_response = requests.get(
    f"{BASE_URL}/ingest/status/{task['task_id']}"
)
print(status_response.json())

# 查询图谱
graph_response = requests.get(
    f"{BASE_URL}/graph/documents/{doc['id']}/graph",
    params={"depth": 2}
)
graph = graph_response.json()
print(f"节点数: {len(graph['nodes'])}")

# 提问
qa_response = requests.post(
    f"{BASE_URL}/qa/ask",
    json={
        "question": "什么是软件工程?",
        "context_limit": 5
    }
)
answer = qa_response.json()
print(f"答案: {answer['answer']}")
```

### cURL 示例

```bash
# 获取文档列表
curl http://localhost:8000/uploads?limit=10

# 上传文档
curl -X POST http://localhost:8000/uploads \
  -F "file=@document.pdf"

# 查询图谱统计
curl http://localhost:8000/graph/stats

# 提问
curl -X POST http://localhost:8000/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "什么是软件工程?"}'
```

### JavaScript/Fetch 示例

```javascript
// 获取文档列表
const docs = await fetch('http://localhost:8000/uploads')
  .then(res => res.json());

// 上传文档
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const upload = await fetch('http://localhost:8000/uploads', {
  method: 'POST',
  body: formData
}).then(res => res.json());

// 查询图谱
const graph = await fetch(`http://localhost:8000/graph/visualize?limit=100`)
  .then(res => res.json());

// 提问
const answer = await fetch('http://localhost:8000/qa/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: '什么是软件工程?',
    context_limit: 5
  })
}).then(res => res.json());
```

## 🧪 API 测试

使用 pytest 运行 API 测试:

```bash
cd server
pytest tests/test_api_routes.py -v
```

使用 Swagger UI 交互式测试:

访问 http://localhost:8000/docs

## 📊 性能考虑

- 使用分页避免大量数据传输
- 图谱查询设置合理的 `limit` 和 `depth`
- 大文件上传使用流式传输
- 启用 HTTP 缓存
- 考虑使用 CDN 加速静态资源

## 📚 相关文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Pydantic 数据验证](https://docs.pydantic.dev/)
- [REST API 设计规范](https://restfulapi.net/)
