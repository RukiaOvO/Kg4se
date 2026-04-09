# 测试脚本使用指南

本目录包含 POW_SE 项目的所有测试代码。

## 📁 测试结构

```
tests/
├── conftest.py              # Pytest 配置和共享 fixtures
├── test_api_routes.py       # API 路由集成测试
├── test_services.py         # 服务层单元测试
├── test_infrastructure.py   # 基础设施集成测试
├── fixtures/                # 测试数据文件
│   └── test_doc.txt
└── graphrag/                # GraphRAG 模块测试
    └── stages/              # 各阶段测试
```

## 🚀 快速开始

### 运行所有测试

```bash
cd server
pytest
```

### 运行特定类型的测试

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 只运行 API 测试
pytest -m api

# 只运行 GraphRAG 测试
pytest -m graphrag
```

### 运行特定文件

```bash
# 运行 API 测试
pytest tests/test_api_routes.py

# 运行服务层测试
pytest tests/test_services.py -v

# 运行特定测试类
pytest tests/test_services.py::TestParserService

# 运行特定测试方法
pytest tests/test_services.py::TestParserService::test_parse_txt
```

## 📊 代码覆盖率

### 生成覆盖率报告

```bash
# 生成 HTML 报告
pytest --cov=. --cov-report=html

# 查看报告
# 浏览器打开 htmlcov/index.html

# 终端显示覆盖率
pytest --cov=. --cov-report=term-missing
```

## 🏷️ 测试标记

测试使用以下标记进行分类:

- `@pytest.mark.unit` - 单元测试(快速,无外部依赖)
- `@pytest.mark.integration` - 集成测试(需要外部服务)
- `@pytest.mark.api` - API 端点测试
- `@pytest.mark.service` - 服务层测试
- `@pytest.mark.graphrag` - GraphRAG 相关测试
- `@pytest.mark.db` - 需要数据库的测试
- `@pytest.mark.ai` - 需要 AI 服务的测试
- `@pytest.mark.slow` - 运行时间较长的测试

### 排除慢速测试

```bash
pytest -m "not slow"
```

### 只运行数据库相关测试

```bash
pytest -m db
```

## 🔧 环境配置

### 测试数据库

测试使用独立的测试数据库,配置环境变量:

```bash
export TEST_NEO4J_URI="bolt://localhost:7687"
export TEST_NEO4J_USER="neo4j"
export TEST_NEO4J_PASSWORD="test_password"
export TEST_REDIS_URL="redis://localhost:6379/1"
```

或创建 `.env.test` 文件:

```env
TEST_NEO4J_URI=bolt://localhost:7687
TEST_NEO4J_USER=neo4j
TEST_NEO4J_PASSWORD=test_password
TEST_REDIS_URL=redis://localhost:6379/1
```

### 跳过需要外部服务的测试

如果没有配置 Neo4j 或 AI 服务,相关测试会自动跳过:

```bash
# 跳过数据库测试
pytest -m "not db"

# 跳过 AI 测试
pytest -m "not ai"

# 跳过所有集成测试
pytest -m "unit"
```

## 📝 编写新测试

### 测试命名规范

- 文件: `test_*.py` 或 `*_test.py`
- 类: `Test*`
- 方法: `test_*`

### 示例测试

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    """我的功能测试"""
    
    def test_basic_functionality(self):
        """测试基本功能"""
        result = my_function()
        assert result == expected_value
    
    @pytest.mark.slow
    def test_complex_scenario(self, sample_data):
        """测试复杂场景"""
        result = process(sample_data)
        assert len(result) > 0
```

### 使用 Fixtures

```python
def test_with_fixture(sample_document, neo4j_test_client):
    """使用共享 fixture 的测试"""
    # sample_document 和 neo4j_test_client 自动注入
    result = process_document(sample_document, neo4j_test_client)
    assert result is not None
```

## 🐛 调试测试

### 详细输出

```bash
pytest -vv
```

### 显示打印语句

```bash
pytest -s
```

### 进入调试模式

```bash
pytest --pdb
```

### 只运行失败的测试

```bash
# 第一次运行
pytest

# 只重新运行失败的
pytest --lf

# 先运行失败的,再运行其他
pytest --ff
```

## 📈 持续集成

测试配置适用于 CI/CD 流程:

```yaml
# .github/workflows/test.yml 示例
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      neo4j:
        image: neo4j:5.15-community
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 🎯 测试最佳实践

1. **保持测试独立**: 每个测试应该能够独立运行
2. **使用有意义的名称**: 测试名称应该清楚描述测试内容
3. **一个测试一个断言**: 尽量每个测试只验证一个行为
4. **使用 fixtures**: 重用测试数据和设置
5. **添加标记**: 使用标记分类测试,便于选择性运行
6. **清理测试数据**: 使用 `clean_test_db` fixture 自动清理
7. **模拟外部服务**: 使用 mock 减少对外部依赖
8. **编写文档**: 为测试类和方法添加文档字符串

## 📚 相关文档

- [Pytest 官方文档](https://docs.pytest.org/)
- [FastAPI 测试指南](https://fastapi.tiangolo.com/tutorial/testing/)
- [Neo4j Python 驱动测试](https://neo4j.com/docs/api/python-driver/current/)

## ❓ 常见问题

### Q: 测试失败但本地运行正常?

A: 检查环境变量配置,确保测试环境与开发环境隔离。

### Q: 如何跳过某个测试?

A: 使用 `@pytest.mark.skip` 或 `pytest.skip()`:

```python
@pytest.mark.skip(reason="功能尚未实现")
def test_future_feature():
    pass
```

### Q: 如何测试异步函数?

A: 使用 `pytest-asyncio`:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result is not None
```

### Q: 测试数据如何清理?

A: 使用 `clean_test_db` fixture 或在 teardown 中清理:

```python
@pytest.fixture
def my_test_data(neo4j_test_client):
    # 设置
    data = setup_data()
    yield data
    # 清理
    cleanup_data(data)
```

---

## 📂 测试文件组织

本项目的测试分为两类:

### 1. 标准 pytest 测试 (推荐用于 CI/CD)

| 文件 | 说明 |
|------|------|
| `test_api_routes.py` | API 路由端点测试 |
| `test_services.py` | 业务服务层测试 |
| `test_infrastructure.py` | 基础设施层测试 |

### 2. 独立验证脚本 (用于快速检查)

| 文件 | 说明 |
|------|------|
| `verify_quick.py` | 快速验证优化实施 |
| `test_domain_optimization.py` | 领域过滤器验证 |
| `test_kg_optimization_integration.py` | 图谱优化集成测试 |
| `test_documents_*.py` | 文档管理功能测试套件 |
| `test_graph_api.py` | 图谱可视化 API 测试 |

详细的测试组织说明请查看 [TESTS_ORGANIZATION.md](TESTS_ORGANIZATION.md)。

---

## 📚 相关资源

- [测试组织结构](TESTS_ORGANIZATION.md) - 完整的测试文件分类和说明
- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [FastAPI 测试指南](https://fastapi.tiangolo.com/tutorial/testing/)
- [Neo4j Python 驱动文档](https://neo4j.com/docs/python-manual/current/)

---

<div align="center">

**编写测试,保证质量! 🧪✨**

Made with ❤️ by POW_SE Team

</div>
