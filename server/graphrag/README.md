# GraphRAG - 图增强检索生成系统

GraphRAG (Graph Retrieval-Augmented Generation) 是 POW_SE 项目的核心知识图谱构建模块,实现了从原始文档到结构化知识图谱的完整流程。

## 📋 目录

- [系统架构](#系统架构)
- [核心概念](#核心概念)
- [8 阶段流水线](#8-阶段流水线)
- [配置说明](#配置说明)
- [API 使用](#api-使用)
- [扩展开发](#扩展开发)

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                     输入: 原始文档                        │
│                   (PDF, TXT, DOCX)                       │
└───────────────────┬──────────────────────────────────────┘
                    │
         ┌──────────▼──────────┐
         │   Stage 0: Chunker  │  语义分块
         │   智能文档切分      │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │   Stage 1: Coref    │  指代消解
         │   实体引用解析      │
         └──────────┬──────────┘
                    │
         ┌──────────▼───────────┐
         │ Stage 2: Entity Link │  实体链接
         │   概念识别与链接     │
         └──────────┬───────────┘
                    │
         ┌──────────▼────────────┐
         │ Stage 3: Claim Extract│  论断抽取
         │   知识三元组提取      │
         └──────────┬────────────┘
                    │
         ┌──────────▼───────────┐
         │ Stage 4: Theme Build │  主题构建
         │   社区聚类与总结     │
         └──────────┬───────────┘
                    │
         ┌──────────▼────────────┐
         │ Stage 5: Predicate    │  谓词治理
         │   关系规范化          │
         └──────────┬────────────┘
                    │
         ┌──────────▼────────────┐
         │ Stage 6: Graph Service│  图谱存储
         │   幂等落库            │
         └──────────┬────────────┘
                    │
         ┌──────────▼────────────┐
         │ Stage 7: Query Service│  智能检索
         │   GraphRAG 查询       │
         └──────────┬────────────┘
                    │
         ┌──────────▼────────────┐
         │ Stage 8: Metrics      │  质量评估
         │   知识图谱指标        │
         └───────────────────────┘
                    │
         ┌──────────▼──────────┐
         │  输出: 知识图谱     │
         │ (Neo4j Graph DB)    │
         └─────────────────────┘
```

## 💡 核心概念

### 1. **Chunk (文本块)**

最小的语义单元,包含:
- 原始文本内容
- 位置信息(索引、页码)
- 向量嵌入(用于语义检索)
- 所属文档引用

### 2. **Claim (论断)**

知识三元组,格式为 `(主体, 谓词, 客体)`:
```python
{
    "subject": "软件工程",
    "predicate": "是",
    "object": "一门学科",
    "confidence": 0.95,
    "evidence": ["chunk_id_1", "chunk_id_2"]
}
```

### 3. **Concept (概念)**

知识图谱中的实体节点:
- **名称**: 规范化的概念名
- **类型**: 概念分类(技术、方法、工具等)
- **属性**: 描述、别名、定义等
- **关系**: 与其他概念的连接

### 4. **Theme (主题)**

概念的聚类社区:
- 相关概念的集合
- 社区摘要
- 层次结构

## 🔄 8 阶段流水线

### Stage 0: 语义分块 (Chunker)

**目标**: 将长文档切分为语义连贯的文本块

**算法**:
```python
from graphrag.stages.stage0_chunker import SemanticChunker

chunker = SemanticChunker(
    chunk_size=512,      # 目标块大小
    overlap=50,          # 重叠 token 数
    strategy="semantic"  # 语义分块策略
)

chunks = await chunker.chunk(document)
```

**输出**: 
- 文本块列表
- 每块包含位置信息和向量嵌入

**配置参数**:
- `chunk_size`: 512-1024 tokens
- `overlap`: 10-50 tokens
- `min_chunk_size`: 100 tokens

---

### Stage 1: 指代消解 (Coreference Resolution)

**目标**: 解析代词和引用,明确实体指向

**示例**:
```
输入: "软件工程很重要。它包含多个阶段。"
输出: "软件工程很重要。软件工程包含多个阶段。"
```

**技术**:
- 使用 NLP 模型识别指代关系
- 替换代词为明确实体
- 保持语义完整性

---

### Stage 2: 实体链接 (Entity Linking)

**目标**: 识别文本中的概念实体并链接到知识库

**流程**:
1. **实体识别**: 提取候选实体
2. **消歧**: 解决同名实体歧义
3. **链接**: 连接到已有概念或创建新概念

**配置** (`config/ontology.yaml`):
```yaml
concepts:
  - name: 软件工程
    type: Discipline
    aliases: ["SE", "Software Engineering"]
  
  - name: 需求分析
    type: Phase
    parent: 软件工程
```

---

### Stage 3: 论断抽取 (Claim Extraction)

**目标**: 从文本中提取结构化知识三元组

**Prompt 模板** (`prompts/claim_extraction.txt`):
```
从以下文本中提取知识三元组:

文本: {text}

要求:
1. 格式: (主体, 谓词, 客体)
2. 谓词使用规范词汇
3. 提供置信度(0-1)
4. 引用证据块ID

示例:
- (软件工程, 包含, 需求分析) [0.95] [chunk_1]
```

**输出**:
```json
{
  "claims": [
    {
      "subject": "软件工程",
      "predicate": "包含",
      "object": "需求分析",
      "confidence": 0.95,
      "evidence": ["chunk_1", "chunk_2"]
    }
  ]
}
```

---

### Stage 4: 主题构建 (Theme Building)

**目标**: 将相关概念聚类形成主题社区

**算法**:
- **Louvain 社区检测**: 识别紧密连接的概念组
- **层次聚类**: 构建多层主题结构
- **摘要生成**: 为每个主题生成描述性摘要

**示例**:
```
主题: "软件开发流程"
概念: [需求分析, 系统设计, 编码实现, 软件测试]
摘要: "描述软件开发的完整生命周期..."
```

---

### Stage 5: 谓词治理 (Predicate Governance)

**目标**: 规范化关系类型,合并同义谓词

**配置** (`config/predicates.yaml`):
```yaml
predicates:
  - canonical: "包含"
    aliases: ["包括", "含有", "涵盖"]
    domain: "组成关系"
  
  - canonical: "依赖"
    aliases: ["依赖于", "基于", "需要"]
    domain: "依赖关系"
```

**规则**:
1. 将同义谓词映射到规范形式
2. 验证谓词的领域适用性
3. 合并重复关系

---

### Stage 6: 图谱服务 (Graph Service)

**目标**: 将结构化知识持久化到 Neo4j

**幂等性保证**:
- 使用 `MERGE` 而非 `CREATE` 避免重复
- 基于唯一标识符(ID、checksum)去重
- 增量更新而非全量替换

**Cypher 示例**:
```cypher
MERGE (c:Concept {id: $concept_id})
ON CREATE SET c.name = $name, c.created_at = datetime()
ON MATCH SET c.updated_at = datetime()

MERGE (c1)-[r:CONTAINS]->(c2)
ON CREATE SET r.weight = $weight
```

---

### Stage 7: 查询服务 (Query Service)

**目标**: 实现基于图谱的智能检索

**检索策略**:

1. **语义检索**: 向量相似度搜索
2. **图结构检索**: 关系路径查询
3. **混合检索**: 结合语义和结构

**示例查询**:
```python
from graphrag.stages.stage7_query_service import QueryService

query_service = QueryService()

# 语义搜索
results = await query_service.semantic_search(
    query="什么是软件工程?",
    top_k=5
)

# 图路径查询
paths = await query_service.find_paths(
    start="软件工程",
    end="敏捷开发",
    max_depth=3
)
```

---

### Stage 8: 指标评估 (Metrics Service)

**目标**: 评估知识图谱质量

**指标**:

| 指标类别 | 指标名称 | 描述 |
|---------|---------|------|
| 完整性 | 覆盖率 | 文档知识点的覆盖比例 |
| 准确性 | 三元组准确率 | 正确论断的比例 |
| 一致性 | 冲突率 | 矛盾知识的数量 |
| 连接性 | 平均度数 | 节点平均连接数 |
| 社区性 | 模块度 | 社区划分质量 |

```python
from graphrag.stages.stage8_metrics_service import MetricsService

metrics = await MetricsService().evaluate()

print(f"节点数: {metrics['node_count']}")
print(f"边数: {metrics['edge_count']}")
print(f"平均度数: {metrics['avg_degree']}")
print(f"连通分量: {metrics['components']}")
```

## ⚙️ 配置说明

### 本体配置 (`config/ontology.yaml`)

定义领域概念的层次结构:

```yaml
domain: 软件工程

concepts:
  - name: 软件工程
    type: Discipline
    description: "系统化、规范化、可量化的软件开发方法"
    
  - name: 需求分析
    type: Phase
    parent: 软件工程
    properties:
      stage_order: 1
      deliverable: "需求规格说明书"
```

### 谓词配置 (`config/predicates.yaml`)

规范关系类型:

```yaml
predicates:
  - canonical: "包含"
    aliases: ["包括", "含有"]
    inverse: "属于"
    transitive: true
    
  - canonical: "依赖"
    aliases: ["依赖于", "基于"]
    inverse: "被依赖"
    transitive: true
```

### 阈值配置 (`config/thresholds.yaml`)

控制质量标准:

```yaml
extraction:
  min_confidence: 0.7      # 最低置信度
  max_claims_per_chunk: 10 # 每块最多论断数

linking:
  similarity_threshold: 0.85  # 实体相似度阈值
  max_candidates: 5          # 最多候选实体

community:
  min_community_size: 3      # 最小社区大小
  resolution: 1.0            # 社区检测分辨率
```

## 🔌 API 使用

### 完整流水线运行

```python
from graphrag import GraphRAGPipeline

# 初始化流水线
pipeline = GraphRAGPipeline(
    neo4j_client=neo4j_client,
    ai_client=ai_client
)

# 处理文档
result = await pipeline.process_document(
    document_id="doc_001",
    document_text="软件工程的内容...",
    stages=[0, 1, 2, 3, 4, 5, 6]  # 运行哪些阶段
)

print(f"处理完成: {result['chunks_count']} 块")
print(f"提取论断: {result['claims_count']} 个")
print(f"识别概念: {result['concepts_count']} 个")
```

### 单阶段运行

```python
# 仅运行 Stage 3 (论断抽取)
from graphrag.stages.stage3_claim_extractor import ClaimExtractor

extractor = ClaimExtractor()
chunks = load_chunks("doc_001")

claims = await extractor.extract_claims(chunks)
```

### 增量更新

```python
# 更新已有文档
await pipeline.update_document(
    document_id="doc_001",
    new_content="新增内容...",
    incremental=True  # 增量模式
)
```

## 🛠️ 扩展开发

### 添加新的处理阶段

1. 在 `stages/` 下创建新文件:

```python
# stages/stage9_my_stage.py

from graphrag.models.chunk import Chunk
from typing import List

class MyStage:
    """我的自定义处理阶段"""
    
    async def process(self, chunks: List[Chunk]) -> List[Chunk]:
        """处理逻辑"""
        processed = []
        for chunk in chunks:
            # 自定义处理
            chunk.custom_field = "value"
            processed.append(chunk)
        return processed
```

2. 注册到流水线:

```python
# __init__.py
from .stages.stage9_my_stage import MyStage

STAGES = {
    0: SemanticChunker,
    # ... 其他阶段
    9: MyStage
}
```

### 自定义 Prompt

修改 `prompts/` 下的模板文件:

```
# prompts/my_custom_extraction.txt

你是一个知识提取专家。从以下文本中提取{target_type}:

文本:
{text}

要求:
1. {requirement_1}
2. {requirement_2}

输出格式:
{output_format}
```

使用:

```python
from graphrag.utils.text_processing import load_prompt

prompt = load_prompt("my_custom_extraction.txt")
filled = prompt.format(
    target_type="概念",
    text=chunk_text,
    requirement_1="准确性优先",
    output_format="JSON"
)
```

### 自定义验证器

```python
# utils/my_validator.py

from graphrag.utils.validation import BaseValidator

class MyValidator(BaseValidator):
    """自定义验证器"""
    
    def validate_claim(self, claim: dict) -> bool:
        """验证论断是否符合领域规则"""
        # 自定义验证逻辑
        if claim["confidence"] < 0.8:
            return False
        return True
```

## 📊 性能优化

### 批处理

```python
# 批量处理多个文档
documents = load_documents()

for batch in chunk_list(documents, batch_size=10):
    await pipeline.process_batch(batch)
```

### 并发处理

```python
import asyncio

tasks = [
    pipeline.process_document(doc_id, doc_text)
    for doc_id, doc_text in documents
]

results = await asyncio.gather(*tasks)
```

### 缓存策略

```python
from graphrag.utils.embedding import CachedEmbedding

# 使用缓存的向量生成
embedder = CachedEmbedding(
    cache_dir="./cache/embeddings",
    ttl=86400  # 24小时过期
)
```

## 🐛 调试与日志

### 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("graphrag")
logger.setLevel(logging.DEBUG)
```

### 中间结果保存

```python
# 保存每个阶段的输出
pipeline = GraphRAGPipeline(
    save_intermediate=True,
    output_dir="./debug_output"
)
```

## 📚 相关资源

- [GraphRAG 论文](https://arxiv.org/abs/2404.16130)
- [Neo4j 图数据库文档](https://neo4j.com/docs/)
- [向量检索最佳实践](https://www.pinecone.io/learn/)

## 🤝 贡献指南

欢迎提交改进建议和 PR!

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交改动 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE) 文件
