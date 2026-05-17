# 测试说明文档

本目录包含项目所有模块的测试代码，包括GraphRAG流水线测试、服务层测试和API测试。

## 目录结构

```
tests/
├── README.md                    # 本文件
├── TEST_GUIDE.md                # 测试使用指南
├── QUICK_REFERENCE.md           # 测试快速参考
├── TEST_FIXES_SUMMARY.md        # 单元测试修复记录
├── conftest.py                  # Pytest 配置和共享 fixtures
├── test_api_routes.py           # API 路由测试
├── test_services.py             # 服务层测试
├── test_infrastructure.py       # 基础设施层测试
├── test_infra.py                # 基础设施模块测试
├── test_evaluation.py           # 评估模块测试
├── test_graph_api.py            # 图谱 API 测试
├── test_documents_code.py       # 文档代码验证
├── test_documents_neo4j.py      # 文档 Neo4j 测试
├── test_documents_integration.py   # 文档集成测试
├── test_documents_fullstack.py     # 文档全栈测试
├── test_documents_final.py         # 文档最终验证
├── test_domain_optimization.py     # 领域优化测试
├── test_kg_optimization_integration.py  # 图谱优化集成测试
├── test_services_coverage.py     # 服务层覆盖率
├── test_services_coverage_extended.py  # 服务层覆盖率扩展
├── test_infra_coverage.py        # 基础设施覆盖率
├── test_infra_coverage_extended.py    # 基础设施覆盖率扩展
├── test_routes_coverage_extended.py   # 路由覆盖率扩展
├── verify_quick.py               # 快速验证脚本
├── run_tests.sh                  # 交互式测试菜单
├── fixtures/                     # 测试数据
│   └── test_doc.txt
└── graphrag/                     # GraphRAG 模块测试
    ├── test_config.py            # 配置测试
    ├── test_utils_advanced.py    # 高级工具测试
    ├── test_utils_coverage.py    # 工具覆盖率测试
    ├── utils/                    # 测试工具
    │   ├── domain_filter.py      # 领域过滤
    │   └── test_claim_utils.py   # 论断工具测试
    └── stages/                   # 各阶段测试
        ├── test_stage0_chunker.py         # Stage 0
        ├── test_stage0_2_manual.py        # Stage 0 手动测试
        ├── test_stage1_coref.py           # Stage 1
        ├── test_stage2_entity_linker.py   # Stage 2
        ├── test_stage3_claim_extractor.py # Stage 3
        ├── test_stage3_claim_extractor_unit.py  # Stage 3 单元
        ├── test_stage6_theme_builder.py   # Stage 6
        └── test_stage6_theme_builder_unit.py    # Stage 6 单元
```

## 快速开始

### 1. 安装测试依赖

```bash
cd server
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### 2. 运行测试

#### 运行所有测试

```bash
# 从项目根目录
pytest tests/ -v
```

#### 运行单个阶段的测试

```bash
# 阶段 0: 篇章切分
pytest tests/graphrag/stages/test_stage0_chunker.py -v

# 阶段 1: 指代消解
pytest tests/graphrag/stages/test_stage1_coref.py -v
```

#### 运行手动测试脚本

```bash
# 快速验证
python tests/verify_quick.py

# 阶段 0 手动测试
python tests/graphrag/stages/test_stage0_2_manual.py
```

### 3. 查看测试覆盖率

```bash
pytest tests/ --cov=server.graphrag --cov-report=html
open htmlcov/index.html
```

## 测试类型

### 单元测试

测试每个阶段的独立功能，位于 `tests/graphrag/stages/`。

### 集成测试

测试多个阶段的协作，位于 `tests/integration/`。

### 端到端测试

测试完整的 API 流程，位于 `tests/e2e/`。

### 手动测试脚本

用于交互式测试和调试，位于 `tests/scripts/`。

## 详细文档

请参考 [TEST_GUIDE.md](TEST_GUIDE.md) 获取完整的测试指南。

