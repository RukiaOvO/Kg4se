# 🧪 测试快速参考

## 📍 快速开始

```bash
# 1. 进入测试目录
cd ../tests

# 2. 运行交互式测试脚本 (推荐)
./run_tests.sh

# 3. 或直接运行特定测试
python verify_quick.py
```

---

## 📚 测试文件分类

### ⚡ 快速验证 (无需服务器)

```bash
python verify_quick.py                        # 配置和文件检查
python test_domain_optimization.py            # 领域过滤器验证
python test_kg_optimization_integration.py    # 实体/关系类型验证
python test_documents_code.py                 # 代码实现检查
```

### 🗄️ 数据库测试 (需要 Neo4j)

```bash
python test_documents_neo4j.py                # Neo4j 查询测试
```

### 🌐 API 测试 (需要服务器运行)

```bash
# 先启动服务器: cd .. && python main.py

python test_graph_api.py                      # 图谱可视化 API
python test_documents_fullstack.py            # 文档管理全栈测试
python test_documents_final.py                # 文档管理 API 验证
```

### 🧩 pytest 标准测试

```bash
cd ..

# 按标记运行
pytest -m unit -v              # 单元测试
pytest -m integration -v       # 集成测试
pytest -m api -v               # API 测试
pytest -m graphrag -v          # GraphRAG 测试

# 按文件运行
pytest tests/test_api_routes.py -v
pytest tests/test_services.py -v
pytest tests/test_infrastructure.py -v

# 生成覆盖率报告
pytest --cov=. --cov-report=html --cov-report=term
```

---

## 🎯 常用命令速查

| 场景 | 命令 |
|------|------|
| **首次验证** | `./run_tests.sh` 选择 1 |
| **检查配置** | `python verify_quick.py` |
| **代码检查** | `python test_documents_code.py` |
| **测试 API** | `python test_graph_api.py` |
| **单元测试** | `pytest -m unit -v` |
| **集成测试** | `pytest -m integration -v` |
| **测试覆盖率** | `pytest --cov=. --cov-report=html` |
| **查看报告** | `firefox htmlcov/index.html` |

---

## 🔧 测试环境准备

### 1. 安装依赖

```bash
cd ..
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio
```

### 2. 配置环境变量

在 `../.env` 中配置:

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_api_key
```

### 3. 启动基础服务

```bash
# 使用 Docker Compose
cd ../..
docker-compose up -d neo4j redis

# 或手动启动
# Neo4j: 访问 http://localhost:7474
# Redis: redis-server
```

---

## 📊 测试标记说明

| 标记 | 说明 | 示例 |
|------|------|------|
| `@pytest.mark.unit` | 快速单元测试,无外部依赖 | 纯函数、工具类测试 |
| `@pytest.mark.integration` | 集成测试,需要数据库 | Neo4j、Redis 测试 |
| `@pytest.mark.api` | API 端点测试 | FastAPI 路由测试 |
| `@pytest.mark.slow` | 耗时测试 (> 5s) | 大数据量、复杂处理 |
| `@pytest.mark.graphrag` | GraphRAG 管道测试 | 8 阶段处理流程 |
| `@pytest.mark.db` | 数据库相关测试 | 查询、事务 |
| `@pytest.mark.ai` | AI 服务测试 | OpenAI API 调用 |

---

## 🐛 故障排查

### Neo4j 连接失败

```bash
# 检查 Neo4j 状态
docker-compose ps neo4j

# 查看日志
docker-compose logs neo4j

# 重启 Neo4j
docker-compose restart neo4j
```

### Redis 连接失败

```bash
# 检查 Redis
redis-cli ping

# 启动 Redis
docker-compose up -d redis
```

### ModuleNotFoundError

```bash
# 确保在正确的目录
cd ..

# 安装依赖
pip install -r requirements.txt

# 检查 Python 路径
python -c "import sys; print(sys.path)"
```

### pytest 找不到测试

```bash
# 检查 pytest 配置
cat pytest.ini

# 使用 -v 查看详细信息
pytest -v --collect-only

# 指定测试路径
pytest tests/ -v
```

---

## 📖 详细文档

- [完整测试指南](TEST_GUIDE.md) - 测试运行和编写详细说明
- [README](README.md) - 测试文件分类和用途

---

## 💡 测试技巧

### 只运行失败的测试

```bash
pytest --lf  # last-failed
```

### 运行特定测试

```bash
# 按名称过滤
pytest -k "test_upload"

# 运行单个测试
pytest tests/test_api_routes.py::TestUploadAPI::test_list_documents
```

### 显示详细输出

```bash
pytest -v -s  # -s 显示 print 输出
```

### 并行运行测试 (需要 pytest-xdist)

```bash
pip install pytest-xdist
pytest -n auto  # 自动检测 CPU 核心数
```

---

<div align="center">

**保持测试绿色! 🧪✅**

Made with ❤️ by Kg4se Team

</div>
