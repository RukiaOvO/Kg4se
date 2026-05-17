<div align="center">

# 🎓 Kg4se

### Software Engineering Knowledge Graph Platform

Multi-modal Knowledge Graph incremental construction platform for the Software Engineering course

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Vue 3](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org/)
[![Neo4j](https://img.shields.io/badge/neo4j-5.x-008CC1.svg)](https://neo4j.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

</div>

---

## Tech Stack

### Frontend

- Vue 3 + TypeScript + Vite
- Naive UI / ECharts / Cytoscape.js
- Pinia (state), Vue Router, vue-i18n

### Backend

- FastAPI on Python 3.11
- Neo4j 5.x, Redis 6.x, RQ queue
- AI providers: OpenAI / Anthropic, GraphRAG pipeline

### Infrastructure

- Docker / Docker Compose
- Nginx reverse proxy

## Project Structure

```text
Kg4se/
├── DOCUMENTATION_INDEX.md      # Documentation index
├── app/vue/                    # Frontend app
│   ├── src/                    # Views, components, stores, api
│   │   ├── api/               # API service layer
│   │   ├── views/             # Page components
│   │   │   ├── Dashboard.vue   # Dashboard
│   │   │   ├── Upload.vue      # Document upload
│   │   │   ├── Documents.vue   # Document management
│   │   │   ├── Graph.vue       # Graph visualization
│   │   │   ├── Query.vue       # Q&A system
│   │   │   ├── KnowledgeCard.vue # Knowledge cards
│   │   │   ├── Evaluation.vue  # Quality evaluation
│   │   │   ├── Status.vue      # Processing status
│   │   │   └── Settings.vue    # System settings
│   │   ├── components/        # Shared components
│   │   ├── stores/            # Pinia state management
│   │   └── i18n/              # Internationalization
│   └── DEVELOPMENT_GUIDE.md    # Frontend guide
├── server/                     # Backend service
│   ├── main.py                 # FastAPI entry
│   ├── config/                 # Configuration management
│   │   ├── config_manager.py   # Config manager
│   │   ├── instances.py        # Service instance init
│   │   └── settings.py         # Environment settings
│   ├── infra/                  # Infra (Neo4j/AI/storage/queue)
│   │   └── README.md
│   ├── models/                 # Data models
│   │   ├── document.py         # Document/Chunk/Triplet models
│   │   ├── graph.py            # Graph models
│   │   ├── knowledge_card.py   # Knowledge card models
│   │   └── README.md
│   ├── services/               # Business services
│   │   ├── parser.py           # Document parser (OCR/Docling)
│   │   ├── graphrag_pipeline_service.py # GraphRAG pipeline
│   │   └── README.md
│   ├── routes/                 # API routes
│   │   ├── evaluation.py       # Evaluation API
│   │   ├── knowledge_card.py   # Knowledge card API
│   │   └── README.md
│   ├── graphrag/               # GraphRAG 9-stage pipeline
│   │   ├── stages/             # Stage implementations (0-8)
│   │   ├── api/                # GraphRAG API
│   │   ├── config/             # YAML configs
│   │   ├── models/             # GraphRAG models
│   │   └── utils/              # Utilities
│   ├── prompts/                # Prompt templates
│   │   ├── graphrag/           # GraphRAG prompts
│   │   └── triplet_extraction/ # Triplet extraction prompts
│   ├── evaluation/             # Evaluation module
│   │   ├── graph_quality.py    # Graph quality eval
│   │   └── answer_quality.py   # Answer quality eval
│   ├── tests/                  # Tests and guides
│   └── requirements.txt        # Python dependencies
└── docker-compose.yml
```

## Quick Start

### Prerequisites

| Component | Version |
|-----------|---------|
| Python | 3.11 (>=3.8 works) |
| Node.js | 18+ |
| Neo4j | 5.26-community |
| Redis | 7.4.7-alpine |
| Docker (optional) | 20.10+ |

### Using Docker Compose (recommended)

```bash
# Clone
git clone <repository-url>
cd Kg4se

# Start Neo4j + Redis
docker-compose up -d
```

### Local development

```bash
# Backend
cd server

cp .env.test .env # Linux/Mac
copy .env.test .env # Windows

python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd app/vue
npm install
npm run dev
```

### Access

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | <http://localhost:3000> | Vue 3 UI |
| Backend API | <http://localhost:8000> | FastAPI service |
| API Docs | <http://localhost:8000/docs> | Swagger UI |
| Neo4j Console | <http://localhost:7474> | Graph DB console |

## Features

### Document management

- Parse PDF / DOCX / TXT / Markdown
- Incremental processing, progress tracking, history snapshots

### Knowledge graph (GraphRAG)

- 9-stage pipeline: chunk → coref → link → extract → predicate → store → theme → metrics → query
- Idempotent Neo4j MERGE storage with deduplication
- Configurable ontology, predicates, and thresholds

### Visualization

- Cytoscape.js interactive graph, multiple layouts
- Filtering, export, statistics

### QA & knowledge cards

- GraphRAG Q&A with entity grounding and context augmentation
- Concept cards, path analysis, tag clouds

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP/WebSocket
┌────────────────────▼─────────────────────────────────────────┐
│                        API (FastAPI)                         │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                     Services (Logic)                         │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                    GraphRAG 9 Stages                         │
└────────────────────┬─────────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────────┐
│                    Storage (Neo4j/Redis)                     │
└──────────────────────────────────────────────────────────────┘
```

## Documentation

| Doc | Description |
|-----|-------------|
| `DOCUMENTATION_INDEX.md` | Documentation index & learning path |
| `server/infra/README.md` | Infra: AI providers, Neo4j, storage, queue |
| `server/models/README.md` | Data models and validation |
| `app/vue/DEVELOPMENT_GUIDE.md` | Frontend development guide |
| `server/graphrag/README.md` | GraphRAG pipeline |
| `server/routes/README.md` | API design and examples |
| `server/services/README.md` | Business services |
| `server/tests/TEST_GUIDE.md` | Testing guide and markers |

## Testing

```bash
cd server
pytest -m unit             # fast unit tests
pytest -m integration      # requires Neo4j/Redis
pytest -m api              # FastAPI route tests
pytest -m graphrag         # GraphRAG pipeline tests
pytest --cov=. --cov-report=html --cov-report=term-missing
```

> **Note**: Install `pytest-cov` before running coverage tests: `pip install pytest-cov`