<div align="center">

# 🎓 POW_SE

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
POW/
├── DOCUMENTATION_INDEX.md      # Documentation index
├── app/vue/                    # Frontend app
│   ├── src/                    # Views, components, stores, api
│   └── DEVELOPMENT_GUIDE.md    # Frontend guide
├── server/                     # Backend service
│   ├── main.py                 # FastAPI entry
│   ├── infra/                  # Infra (Neo4j/AI/storage/queue)
│   │   └── README.md
│   ├── models/                 # Data models
│   │   └── README.md
│   ├── services/               # Business services
│   ├── routes/                 # API routes
│   ├── graphrag/               # GraphRAG 8-stage pipeline
│   └── tests/                  # Tests and guides
└── docker-compose.yml
```

## Quick Start

### Prerequisites

| Component | Version |
|-----------|---------|
| Python | 3.11 (>=3.8 works) |
| Node.js | 18+ |
| Neo4j | 5.x |
| Redis | 6.x |
| Docker (optional) | 20.10+ |

### Using Docker Compose (recommended)

```bash
# Clone
git clone <repository-url>
cd POW

# Start frontend + backend + Neo4j + Redis
docker-compose up -d
```

### Local development

```bash
# Backend
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd app/vue
npm install
npm run dev -- --port 3000
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

- 8-stage pipeline: chunk → coref → link → extract → theme → predicate → store → query
- Idempotent Neo4j MERGE storage with deduplication

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
│                    GraphRAG 8 Stages                         │
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
pytest                     # default fast set
pytest -m unit             # unit only
pytest -m integration      # requires Neo4j/Redis
pytest -m api              # FastAPI routes
pytest --cov=. --cov-report=html
```

## Contributors

Ye Yu · Hongbang Zhang · Jingwen Zhang · Jingyi Wang · Jiayi Li · Shaohua Huang · Tianshuo Zhang · Fangbo Liu · Xin Chen

## License

MIT License