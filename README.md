<div align="center">

# 🎓 Kg4se

### 软件工程知识图谱平台

**面向《软件工程》课程的多模态知识图谱增量式构建平台**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org/)
[![Neo4j](https://img.shields.io/badge/neo4j-5.x-008CC1.svg)](https://neo4j.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

</div>

---

## 技术栈

### 前端

- Vue 3 + TypeScript + Vite
- Naive UI / ECharts / Cytoscape.js
- 状态管理: Pinia, 路由: Vue Router, 国际化: vue-i18n

### 后端

- FastAPI + Python 3.11
- Neo4j 5.x, Redis 6.x, RQ 队列
- AI 集成: OpenAI / Anthropic 等多模型 (GraphRAG 流水线)

### 基础设施

- Docker / Docker Compose
- Nginx 反向代理

## 项目结构

```text
Kg4se/
├── DOCUMENTATION_INDEX.md      # 文档总览/导航
├── app/vue/                    # 前端应用
│   ├── src/                    # 业务页面、组件、stores、api
│   │   ├── api/                # API服务层(index.ts, services.ts)
│   │   ├── views/              # 页面组件
│   │   │   ├── Dashboard.vue   # 仪表盘
│   │   │   ├── Upload.vue      # 文档上传
│   │   │   ├── Documents.vue   # 文档管理
│   │   │   ├── Graph.vue       # 图谱可视化
│   │   │   ├── Query.vue       # 智能问答
│   │   │   ├── KnowledgeCard.vue # 知识卡片
│   │   │   ├── Evaluation.vue  # 质量评估
│   │   │   ├── Status.vue      # 处理状态
│   │   │   └── Settings.vue    # 系统设置
│   │   ├── components/         # 通用组件
│   │   ├── stores/             # Pinia状态管理
│   │   └── i18n/               # 国际化配置
│   └── DEVELOPMENT_GUIDE.md    # 前端开发指南
├── server/                     # 后端服务
│   ├── main.py                 # FastAPI 入口
│   ├── config/                 # 配置管理(新增)
│   │   ├── config_manager.py   # 配置管理器
│   │   ├── instances.py        # 服务实例初始化
│   │   └── settings.py         # 环境变量配置
│   ├── infra/                  # 基础设施(Neo4j/AI/存储/队列)
│   │   └── README.md
│   ├── models/                 # 数据模型
│   │   ├── document.py         # 文档/Chunk/三元组模型
│   │   ├── graph.py            # 图谱模型
│   │   ├── knowledge_card.py   # 知识卡片模型
│   │   └── README.md
│   ├── services/               # 业务服务
│   │   ├── parser.py           # 文档解析(集成OCR/Docling)
│   │   ├── graphrag_pipeline_service.py # GraphRAG流水线服务
│   │   └── README.md
│   ├── routes/                 # API 路由
│   │   ├── evaluation.py       # 评估API
│   │   ├── knowledge_card.py   # 知识卡片API
│   │   └── README.md
│   ├── graphrag/               # GraphRAG 九阶段流水线
│   │   ├── stages/             # 阶段实现(Stage 0-8)
│   │   ├── api/                # GraphRAG API接口
│   │   ├── config/             # YAML配置(本体/谓词/阈值)
│   │   ├── models/             # GraphRAG数据模型
│   │   ├── utils/              # 工具函数
│   │   └── README.md
│   ├── prompts/                # Prompt模板管理
│   │   ├── graphrag/           # GraphRAG相关Prompt
│   │   └── triplet_extraction/ # 三元组提取Prompt
│   ├── evaluation/             # 评估模块
│   │   ├── graph_quality.py    # 图谱质量评估
│   │   └── answer_quality.py   # 回答质量评估
│   ├── tests/                  # 测试套件与指南
│   └── requirements.txt        # Python依赖
└── docker-compose.yml
```

## 快速开始

### 📋 环境要求

| 组件 | 版本 |
|------|------|
| Python | 3.11 (>=3.8 可运行) |
| Node.js | 18+ |
| Neo4j | 5.26-community |
| Redis | 7.4.7-alpine |
| Docker (可选) | 20.10+ |

### 🐳 使用 Docker Compose 部署数据库

```bash
# 克隆项目
git clone <repository-url>
cd Kg4se

# 启动 Neo4j + Redis
docker-compose up -d
```

### 💻 本地开发

```bash
# 后端
cd server

# 环境配置
cp .env.test .env # Linux/Mac
copy .env.test .env # Windows

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd app/vue
npm install
npm run dev
```

### 🌐 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | <http://localhost:3000> | Vue 3 界面 |
| 后端 API | <http://localhost:8000> | FastAPI 服务 |
| API 文档 | <http://localhost:8000/docs> | Swagger UI |
| Neo4j 控制台 | <http://localhost:17474> | 图数据库管理 |

---

## ✨ 功能特性

### 📚 文档管理

- 多格式解析: PDF / DOCX / TXT / Markdown
- 增量处理: 仅处理新增片段, 支持内容快照与进度追踪

### 🧠 知识图谱 (GraphRAG)

- 九阶段流水线 (默认运行核心 1-7 阶段): 分块→指代消解→实体链接→Claim提取→谓词治理→图谱存储→主题构建→度量服务→查询服务
- Neo4j MERGE 幂等存储, 去重与关联

### 🎨 可视化与交互

- Cytoscape.js 交互式图谱 + 多布局
- 过滤/导出/统计视图

### 💬 智能问答与知识卡

- GraphRAG 问答, 实体识别 + 上下文增强
- 概念卡片、路径分析、标签云

### 📊 质量评估

- LLM回答质量对比评估（GraphRAG vs RAG vs LLM）
- 量化指标展示与可视化

---

## 🏗️ 架构设计

### 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        前端层 (Vue 3)                         │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ 文档   │  │ 图谱   │  │ 知识   │  │ 问答   │  │ 设置   │ │
│  │ 管理   │  │ 可视化  │  │ 卡片   │  │ 系统   │  │ 管理   │ │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │
│                          ┌────────────────┐                  │
│                          │ 质量评估      │                  │
│                          │ (Evaluation)  │                  │
│                          └────────────────┘                  │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼─────────────────────────────────────────┐
│                    API 层 (FastAPI)                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ Upload │  │ Graph  │  │ Ingest │  │   QA   │  │Settings│ │
│  │  API   │  │  API   │  │  API   │  │  API   │  │  API   │ │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │
│  ┌────────────────┐  ┌────────────────┐                     │
│  │ KnowledgeCard  │  │  Evaluation    │                     │
│  │     API        │  │     API        │                     │
│  └────────────────┘  └────────────────┘                     │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                   服务层 (Business Logic)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Parser  │  │Extractor │  │  Linker  │  │QA Service│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                          ┌────────────────┐                  │
│                          │ GraphRAG      │                  │
│                          │ Pipeline      │                  │
│                          └────────────────┘                  │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                   GraphRAG 管道 (9 阶段)                      │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│  │分块  │→│消解  │→│链接  │→│提取  │→│治理  │  9 阶段  │
│  │Stage0│  │Stage1│  │Stage2│  │Stage3│  │Stage4│         │
│  └──────┘  └──────┘  └──────┘  └──────┘  └───┬──┘         │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │           │
│  │度量  │←─│主题  │←─│存储  │←─│ ...  │←─────┘           │
│  │Stage7│  │Stage6│  │Stage5│  │      │                   │
│  └──────┘  └──────┘  └──────┘  └──────┘                   │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                    数据层 (Storage)                           │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │    Neo4j     │     │    Redis     │     │  File System │ │
│  │  (图数据库)   │     │   (缓存)      │     │  (文档存储)   │ │
│  └──────────────┘     └──────────────┘     └──────────────┘ │
└──────────────────────────────────────────────────────────────┘
```