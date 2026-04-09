<div align="center">

# 🎓 POW_SE

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
POW/
├── DOCUMENTATION_INDEX.md      # 文档总览/导航
├── app/vue/                    # 前端应用
│   ├── src/                    # 业务页面、组件、stores、api
│   └── DEVELOPMENT_GUIDE.md    # 前端开发指南
├── server/                     # 后端服务
│   ├── main.py                 # FastAPI 入口
│   ├── infra/                  # 基础设施(Neo4j/AI/存储/队列)
│   │   └── README.md
│   ├── models/                 # 数据模型
│   │   └── README.md
│   ├── services/               # 业务服务
│   ├── routes/                 # API 路由
│   ├── graphrag/               # GraphRAG 八阶段流水线
│   └── tests/                  # 测试套件与指南
└── docker-compose.yml
```

## 快速开始

### 📋 环境要求

| 组件 | 版本 |
|------|------|
| Python | 3.11 (>=3.8 可运行) |
| Node.js | 18+ |
| Neo4j | 5.x |
| Redis | 6.x |
| Docker (可选) | 20.10+ |

### 🐳 使用 Docker Compose 部署数据库

```bash
# 克隆项目
git clone <repository-url>
cd POW

# 启动前后端 + Neo4j + Redis
docker-compose up -d
```

### 💻 本地开发

```bash
# 后端
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 前端
cd app/vue
npm install
npm run dev -- --port 3000
```

### 🌐 访问应用

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | <http://localhost:3000> | Vue 3 界面 |
| 后端 API | <http://localhost:8000> | FastAPI 服务 |
| API 文档 | <http://localhost:8000/docs> | Swagger UI |
| Neo4j 控制台 | <http://localhost:7474> | 图数据库管理 |

---

## ✨ 功能特性

### 📚 文档管理

- 多格式解析: PDF / DOCX / TXT / Markdown
- 增量处理: 仅处理新增片段, 支持内容快照与进度追踪

### 🧠 知识图谱 (GraphRAG)

- 八阶段流水线: 切分→消解→链接→提取→主题→谓词治理→存储→查询
- Neo4j MERGE 幂等存储, 去重与关联

### 🎨 可视化与交互

- Cytoscape.js 交互式图谱 + 多布局
- 过滤/导出/统计视图

### 💬 智能问答与知识卡

- GraphRAG 问答, 实体识别 + 上下文增强
- 概念卡片、路径分析、标签云

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
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼─────────────────────────────────────────┐
│                    API 层 (FastAPI)                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐ │
│  │ Upload │  │ Graph  │  │ Ingest │  │   QA   │  │Settings│ │
│  │  API   │  │  API   │  │  API   │  │  API   │  │  API   │ │
│  └────────┘  └────────┘  └────────┘  └────────┘  └────────┘ │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                   服务层 (Business Logic)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Parser  │  │Extractor │  │  Linker  │  │QA Service│    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                   GraphRAG 管道 (8 阶段)                      │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│  │ 切分 │→│ 消解 │→│ 链接 │→│ 提取 │→│ ...  │  8 阶段  │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘         │
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

## 🤝 贡献者

俞烨 · 张鸿榜 · 张璟文 · 王劲毅 · 李嘉艺 · 黄绍华 · 张天硕 · 刘方博 · 陈欣

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。