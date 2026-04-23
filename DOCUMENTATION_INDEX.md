# Kg4se 项目完整文档索引

## 📚 文档导航

本文档提供项目所有模块的文档索引，帮助开发者快速定位所需信息。

---

## 🏗️ 项目架构概览

```
Kg4se/
├── server/                     # 后端服务 (Python + FastAPI)
│   ├── config/               # 配置管理 (新增)
│   │   ├── config_manager.py # 配置管理器
│   │   ├── instances.py      # 服务实例初始化
│   │   └── settings.py       # 环境变量设置
│   ├── infra/                 # 基础设施层
│   ├── models/                # 数据模型
│   ├── services/              # 业务服务
│   ├── routes/                # API路由
│   ├── graphrag/              # 知识图谱RAG (9阶段流水线)
│   │   ├── stages/           # 各阶段实现 (Stage 0-8)
│   │   ├── api/              # GraphRAG API
│   │   ├── config/           # YAML配置
│   │   ├── models/           # GraphRAG模型
│   │   └── utils/            # 工具函数
│   ├── prompts/               # Prompt模板管理
│   ├── evaluation/            # 评估模块
│   │   ├── graph_quality.py  # 图谱质量评估
│   │   └── answer_quality.py # 回答质量评估
│   └── tests/                 # 测试套件
│
├── app/vue/                   # 前端应用 (Vue 3 + TypeScript)
│   └── src/
│       ├── api/              # API服务层
│       ├── views/            # 页面组件
│       │   ├── Dashboard.vue # 仪表盘
│       │   ├── Upload.vue    # 文档上传
│       │   ├── Documents.vue # 文档管理
│       │   ├── Graph.vue     # 图谱可视化
│       │   ├── Query.vue     # 智能问答
│       │   ├── KnowledgeCard.vue # 知识卡片
│       │   ├── Evaluation.vue # 质量评估
│       │   ├── Status.vue    # 处理状态
│       │   └── Settings.vue  # 系统设置
│       ├── components/       # 通用组件
│       ├── stores/           # 状态管理
│       └── router/           # 路由配置
│
├── data/                      # 数据存储
│   ├── neo4j/                # Neo4j数据库
│   └── redis/                # Redis缓存
│
└── docker-compose.yml         # Docker编排
```

---

## 📖 核心文档列表

### 🎯 快速入门

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目README | `/README.md` | 项目简介、安装、运行指南 |
| 文档索引 | `/DOCUMENTATION_INDEX.md` | 文档导航与学习路径 |
| Docker部署 | `/docker-compose.yml` | Docker容器化配置 |

---

### 🔧 后端文档

#### 基础设施层 (Infra)

| 文档 | 路径 | 内容 |
|------|------|------|
| Infra模块说明 | `/server/infra/README.md` | AI提供商、Neo4j客户端、配置管理、队列、存储 |
| AI提供商集成 | `/server/infra/AI_PROVIDERS.md` | 10+AI提供商接入指南 |
| Neo4j操作手册 | `/server/infra/NEO4J_GUIDE.md` | 图数据库操作和优化 |

**核心内容**:
- ✅ 支持OpenAI、Claude、Gemini、通义千问等12个AI提供商
- ✅ Neo4j连接管理（自动重连、批量操作）
- ✅ 配置管理（环境变量、.env文件、config模块）
- ✅ 异步任务队列（Redis）
- ✅ 文件存储服务
- ✅ Neo4j 5.26-community + APOC + GDS 插件

---

#### 数据模型层 (Models)

| 文档 | 路径 | 内容 |
|------|------|------|
| Models模块说明 | `/server/models/README.md` | 所有数据模型定义、请求/响应模型规范 |

**核心模型**:
- `Document`: 文档模型
- `Chunk`: 文本块模型
- `Triplet`: 三元组（知识图谱基本单元）
- `AIExtractionRequest`: AI提取配置
- `KnowledgeCard`: 知识卡片模型
- `Graph`: 图谱节点/边模型

---

#### 业务服务层 (Services)

| 文档 | 路径 | 内容 |
|------|------|------|
| Services模块说明 | `/server/services/README.md` | 业务逻辑服务详解 |
| Parser服务 | `/server/services/PARSER.md` | 文档解析服务 |
| Extractor服务 | `/server/services/EXTRACTOR.md` | 知识抽取服务 |
| EntityLinker服务 | `/server/services/LINKER.md` | 实体链接服务 |

**核心服务**:
- `ParserService`: 支持PDF、Word、Markdown、EPUB等格式，集成Docling和RapidOCR
- `TripletExtractor`: 基于LLM的三元组提取
- `EntityLinker`: 实体去重和链接
- `AISegmenter`: AI智能分段
- `QAService`: 智能问答
- `GraphRAGPipelineService`: GraphRAG完整流水线编排
- `ConfigService`: 配置管理服务

---

#### API路由层 (Routes)

| 文档 | 路径 | 内容 |
|------|------|------|
| Routes模块说明 | `/server/routes/README.md` | API路由和端点文档 |
| API接口文档 | `/server/routes/API_REFERENCE.md` | 完整API参考 |
| 认证授权 | `/server/routes/AUTH.md` | 认证和权限管理 |

**API模块**:
- `/api/uploads`: 文档管理API
- `/api/ingest`: 知识提取API
- `/api/graph`: 图谱可视化API
- `/api/qa`: 智能问答API
- `/api/knowledge-cards`: 知识卡片API
- `/api/settings`: 系统设置API
- `/api/evaluation`: 质量评估API
  - `/evaluation/graph`: 图谱质量分析
  - `/evaluation/answer`: 回答质量对比评估

---

#### GraphRAG模块

| 文档 | 路径 | 内容 |
|------|------|------|
| GraphRAG说明 | `/server/graphrag/README.md` | 知识图谱增量构建pipeline |
| Stage 0: Chunker | `/server/graphrag/stages/STAGE0.md` | 文档智能切分 |
| Stage 1: Coref | `/server/graphrag/stages/STAGE1.md` | 指代消解 |
| Stage 2: Linker | `/server/graphrag/stages/STAGE2.md` | 实体链接 |
| Stage 3: Extractor | `/server/graphrag/stages/STAGE3.md` | 三元组提取 |
| Stage 4: Theme | `/server/graphrag/stages/STAGE4.md` | 主题构建 |
| Stage 5-8 | `/server/graphrag/stages/` | 谓词治理/存储/查询/指标 |

**9阶段Pipeline**:
1. 📄 Stage 0: 篇章切分
2. 🔗 Stage 1: 指代消解
3. 🏷️ Stage 2: 实体链接
4. 📊 Stage 3: Claim提取
5. 🎨 Stage 4: 主题构建
6. ⚖️ Stage 5: 谓词治理
7. 💾 Stage 6: 图谱服务
8. 🔍 Stage 7: 查询服务
9. 📈 Stage 8: 度量服务

---

#### 测试文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 测试组织说明 | `/server/tests/TESTS_ORGANIZATION.md` | 测试分类和运行指南 |
| 测试快速参考 | `/server/tests/QUICK_REFERENCE.md` | 常用测试命令 |
| 测试修复总结 | `/server/tests/TEST_FIXES_SUMMARY.md` | 单元测试修复记录 |

**测试覆盖**:
- ✅ 单元测试: 7个通过
- ✅ 集成测试: 43个通过
- ✅ GraphRAG测试: 17个通过
- 📊 覆盖率: Services 5%, GraphRAG Stages ~15%

---

### 🎨 前端文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 前端架构文档 | `/app/vue/src/README.md` | Vue 3项目架构说明 |
| 开发指南 | `/app/vue/DEVELOPMENT_GUIDE.md` | 前端开发详细指南 |
| 组件库 | `/app/vue/COMPONENTS.md` | 通用组件文档 |
| 状态管理 | `/app/vue/STORES.md` | Pinia状态管理 |

**核心页面**:
- `Dashboard.vue`: 仪表盘（统计数据）
- `Upload.vue`: 文档上传（拖拽/批量）
- `Documents.vue`: 文档管理（列表/搜索）
- `Graph.vue`: 知识图谱可视化（1571行核心代码）
- `Query.vue`: 智能问答（对话界面）
- `KnowledgeCard.vue`: 知识卡片（概念浏览）
- `Evaluation.vue`: 质量评估（图谱质量、回答对比）
- `Status.vue`: 处理状态监控
- `Settings.vue`: 系统设置（AI配置）

**技术亮点**:
- ✅ Cytoscape.js图可视化（5种布局算法）
- ✅ Composition API + TypeScript
- ✅ Naive UI高质量组件
- ✅ Pinia状态管理
- ✅ Vue I18n国际化（中英双语）

---

## 🔍 按功能查找文档

### 文档上传和处理

1. 前端上传界面: `/app/vue/src/views/Upload.vue`
2. 上传API: `/server/routes/upload.py`
3. 文档解析: `/server/services/parser.py` + `/server/services/README.md`
4. AI智能分段: `/server/services/ai_segmenter.py`
5. 测试: `/server/tests/test_services.py`

---

### 知识图谱构建

1. GraphRAG Pipeline: `/server/graphrag/README.md`
2. 各阶段详细文档: `/server/graphrag/stages/STAGE*.md`
3. 三元组提取: `/server/services/extractor.py`
4. 实体链接: `/server/services/linker.py`
5. Neo4j存储: `/server/infra/neo4j_client.py`
6. 测试: `/server/tests/graphrag/stages/`

---

### 图谱可视化

1. 前端可视化: `/app/vue/src/views/Graph.vue`
2. 图谱API: `/server/routes/graph.py`
3. Neo4j查询: `/server/infra/neo4j_client.py`
4. 开发指南: `/app/vue/DEVELOPMENT_GUIDE.md` (第2节)

---

### 智能问答

1. 问答界面: `/app/vue/src/views/Query.vue`
2. QA服务: `/server/services/qa_service.py`
3. QA API: `/server/routes/qa.py`
4. 知识检索: `/server/graphrag/stages/stage7_query_service.py`

---

### AI提供商集成

1. AI提供商文档: `/server/infra/README.md` (AI Providers部分)
2. 配置管理: `/server/infra/config.py`
3. 使用示例: `/server/services/extractor.py`
4. 前端设置: `/app/vue/src/views/Settings.vue`


## 🔗 外部资源

### 技术文档

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [Vue 3官方文档](https://vuejs.org/)
- [Neo4j文档](https://neo4j.com/docs/)
- [Pydantic文档](https://docs.pydantic.dev/)
- [Cytoscape.js文档](https://js.cytoscape.org/)

### 相关论文

- GraphRAG: [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- 知识图谱构建: 相关学术论文
- 实体链接: NEL算法综述
