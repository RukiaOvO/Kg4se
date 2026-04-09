# POW 项目完整文档索引

## 📚 文档导航

本文档提供项目所有模块的文档索引，帮助开发者快速定位所需信息。

---

## 🏗️ 项目架构概览

```
POW/
├── server/                     # 后端服务 (Python + FastAPI)
│   ├── infra/                 # 基础设施层
│   ├── models/                # 数据模型
│   ├── services/              # 业务服务
│   ├── routes/                # API路由
│   ├── graphrag/              # 知识图谱RAG
│   └── tests/                 # 测试套件
│
├── app/vue/                   # 前端应用 (Vue 3 + TypeScript)
│   └── src/
│       ├── api/              # API服务层
│       ├── views/            # 页面组件
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
| 快速开始 | `/QUICKSTART.md` | 5分钟快速上手 |
| Docker部署 | `/DOCKER.md` | Docker容器化部署 |
| 环境配置 | `/ENVIRONMENT.md` | 环境变量和配置说明 |

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
- ✅ 配置管理（环境变量、.env文件）
- ✅ 异步任务队列（Redis）
- ✅ 文件存储服务

---

#### 数据模型层 (Models)

| 文档 | 路径 | 内容 |
|------|------|------|
| Models模块说明 | `/server/models/README.md` | 所有数据模型定义和使用示例 |
| API模型规范 | `/server/models/API_MODELS.md` | 请求/响应模型规范 |

**核心模型**:
- `Document`: 文档模型
- `Chunk`: 文本块模型
- `Triplet`: 三元组（知识图谱基本单元）
- `AIExtractionRequest`: AI提取配置

---

#### 业务服务层 (Services)

| 文档 | 路径 | 内容 |
|------|------|------|
| Services模块说明 | `/server/services/README.md` | 业务逻辑服务详解 |
| Parser服务 | `/server/services/PARSER.md` | 文档解析服务 |
| Extractor服务 | `/server/services/EXTRACTOR.md` | 知识抽取服务 |
| EntityLinker服务 | `/server/services/LINKER.md` | 实体链接服务 |

**核心服务**:
- `ParserService`: 支持PDF、Word、Markdown、EPUB等格式
- `TripletExtractor`: 基于LLM的三元组提取
- `EntityLinker`: 实体去重和链接
- `AISegmenter`: AI智能分段
- `QAService`: 智能问答

---

#### API路由层 (Routes)

| 文档 | 路径 | 内容 |
|------|------|------|
| Routes模块说明 | `/server/routes/README.md` | API路由和端点文档 |
| API接口文档 | `/server/routes/API_REFERENCE.md` | 完整API参考 |
| 认证授权 | `/server/routes/AUTH.md` | 认证和权限管理 |

**API模块**:
- `/api/documents`: 文档管理API
- `/api/upload`: 文件上传API
- `/api/graph`: 图谱可视化API
- `/api/ingest`: 知识提取API
- `/api/qa`: 智能问答API
- `/api/knowledge`: 知识卡片API
- `/api/settings`: 系统设置API

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

**8阶段Pipeline**:
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

---

## 🎓 学习路径推荐

### 新手入门 (第1-3天)

1. 阅读主README: `/README.md`
2. 运行Quick Start: 按照步骤启动项目
3. 前端架构: `/app/vue/src/README.md`
4. 数据模型: `/server/models/README.md`
5. 测试运行: `/server/tests/QUICK_REFERENCE.md`

---

### 后端开发 (第4-7天)

1. **基础设施**:
   - Infra模块: `/server/infra/README.md`
   - Neo4j操作: 学习图数据库查询
   - AI集成: 了解各AI提供商特点

2. **业务服务**:
   - Services模块: `/server/services/README.md`
   - 文档解析: 支持新文件格式
   - 知识抽取: 优化提取算法

3. **API开发**:
   - Routes模块: `/server/routes/README.md`
   - FastAPI框架: 学习路由和中间件
   - API测试: Postman/curl调试

---

### 前端开发 (第8-10天)

1. **Vue基础**:
   - 开发指南: `/app/vue/DEVELOPMENT_GUIDE.md`
   - Composition API: 组件开发规范
   - TypeScript: 类型定义

2. **核心功能**:
   - 图谱可视化: Cytoscape.js实践
   - 状态管理: Pinia使用
   - 组件开发: Naive UI集成

3. **样式和交互**:
   - SCSS编写
   - 响应式设计
   - 动画效果

---

### GraphRAG深入 (第11-14天)

1. Pipeline概览: `/server/graphrag/README.md`
2. 各阶段实现:
   - 文档切分策略
   - 指代消解算法
   - 实体链接机制
   - 主题构建方法
3. 测试和优化:
   - 编写Stage测试
   - 性能profiling
   - 调优参数

---

## 📝 文档编写规范

### 模块文档结构

每个模块的README.md应包含:

```markdown
# 模块名称

## 📋 模块概述
- 核心职责
- 主要功能

## 📁 模块结构
- 文件列表
- 目录说明

## 🔧 核心类/函数
- API文档
- 使用示例

## 💡 使用场景
- 典型用例
- 最佳实践

## 🧪 测试
- 测试覆盖
- 测试示例

## 📚 相关文档
- 链接到其他文档
```

---

## 🔄 文档维护

### 更新频率

- **主文档**: 每个版本发布时更新
- **API文档**: 代码变更后同步更新
- **开发指南**: 每月审查一次
- **测试文档**: 测试变更后更新

### 贡献指南

1. 发现文档问题？提Issue
2. 想改进文档？提PR
3. 新增功能？同步更新文档
4. 重构代码？检查相关文档

---

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

---

## 📞 获取帮助

- **问题反馈**: 在GitHub Issues提交
- **功能建议**: 在Discussions讨论
- **紧急问题**: 联系项目维护者

---
