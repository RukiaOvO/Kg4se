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

**核心内容**:
- ✅ 支持OpenAI、Claude、Gemini、DeepSeek等12个AI提供商
- ✅ Neo4j连接管理（自动重连、批量操作）
- ✅ 配置管理（环境变量、.env文件、config模块）
- ✅ 异步任务队列（Redis + RQ）
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

**核心服务**:
- `ParserFactory`: 支持PDF、Word、Markdown、TXT等格式，集成Docling和RapidOCR
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

**API模块**:
- `/uploads`: 文档上传和管理API
- `/ingest`: 知识抽取任务API
- `/graph`: 图谱可视化与CRUD API
- `/qa`: 智能问答API（含流式响应）
- `/knowledge-cards`: 知识卡片API
- `/settings`: 系统设置与AI配置API
- `/evaluation`: 质量评估API
  - `/evaluation/answer`: 单问题三路对比评估
  - `/evaluation/batch`: 批量数据集评估
  - `/evaluation/pairwise`: 两两成对比较
  - `/evaluation/datasets`: 基准数据集管理

---

#### GraphRAG模块

| 文档 | 路径 | 内容 |
|------|------|------|
| GraphRAG说明 | `/server/graphrag/README.md` | 知识图谱增量构建pipeline |

**9阶段Pipeline (默认运行核心1-7阶段)**:
1. 📄 Stage 0: 篇章切分 (Chunker) — 可选
2. 🔗 Stage 1: 指代消解 (Coreference)
3. 🏷️ Stage 2: 实体链接 (Entity Linking)
4. 📊 Stage 3: Claim提取 (Claim Extraction)
5. ⚖️ Stage 4: 谓词治理 (Predicate Governance)
6. 💾 Stage 5: 图谱存储 (Graph Service)
7. 🎨 Stage 6: 主题构建 (Theme Building)
8. 📈 Stage 7: 度量服务 (Metrics Service)
9. 🔍 Stage 8: 查询服务 (Query Service) — 可选

---

#### 测试文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 测试指南 | `/server/tests/TEST_GUIDE.md` | 测试运行和编写详细说明 |
| 测试快速参考 | `/server/tests/QUICK_REFERENCE.md` | 常用测试命令 |
| 测试修复总结 | `/server/tests/TEST_FIXES_SUMMARY.md` | 单元测试修复记录 |

**测试结构**:
- ✅ 单元测试: `tests/test_services.py`, `tests/graphrag/`
- ✅ 集成测试: `tests/test_api_routes.py`, `tests/test_infrastructure.py`
- ✅ GraphRAG测试: `tests/graphrag/stages/`
- ✅ 快速验证脚本: `tests/verify_quick.py`

---

### 🎨 前端文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 前端架构文档 | `/app/vue/src/README.md` | Vue 3项目架构说明 |
| 开发指南 | `/app/vue/DEVELOPMENT_GUIDE.md` | 前端开发详细指南 |

**核心页面**:
- `Dashboard.vue`: 仪表盘（统计数据）
- `Upload.vue`: 知识构建/文档上传（拖拽/批量）
- `Documents.vue`: 文档管理（列表/搜索）
- `Graph.vue`: 知识图谱可视化
- `KnowledgeCard.vue`: 知识卡片（概念浏览）
- `Evaluation.vue`: 质量评估（LLM-as-a-Judge五维评分）
- `Settings.vue`: 系统设置（AI配置）
- `Status.vue`: 处理状态监控

**技术亮点**:
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
4. 测试: `/server/tests/test_services.py`

---

### 知识图谱构建

1. GraphRAG Pipeline: `/server/graphrag/README.md`
2. 三元组提取: `/server/services/extractor.py`
3. 实体链接: `/server/services/linker.py`
4. Neo4j存储: `/server/infra/neo4j_client.py`
5. 测试: `/server/tests/graphrag/stages/`

---

### 图谱可视化

1. 前端可视化: `/app/vue/src/views/Graph.vue`
2. 图谱API: `/server/routes/graph.py`
3. Neo4j查询: `/server/infra/neo4j_client.py`
4. 开发指南: `/app/vue/DEVELOPMENT_GUIDE.md`

---

### 智能问答

1. QA服务: `/server/services/qa_service.py`
2. QA API: `/server/routes/qa.py`
3. 知识检索: `/server/graphrag/stages/stage8_query_service.py`

---

### AI提供商集成

1. AI提供商文档: `/server/infra/README.md`
2. 配置管理: `/server/config/settings.py`
3. 前端设置: `/app/vue/src/views/Settings.vue`


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
