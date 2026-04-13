"""Triplet extraction service using LLM."""
import json
from typing import List, Optional
from infra.ai_providers import AIProviderFactory, BaseAIClient
from models.document import Triplet, Chunk
from services.config_service import config_service
from prompts import PromptManager


class TripletExtractor:
    """Extract triplets from text using LLM."""

    def __init__(self):
        self.client: Optional[BaseAIClient] = None
        self.provider = None
        self.model = None
        self.prompt_manager = PromptManager()

        try:
            # 从数据库读取运行时配置
            ai_config = config_service.get_ai_provider_config()
            self.provider = ai_config["provider"]
            api_key = ai_config["api_key"]
            model = ai_config["model"]
            base_url = ai_config["base_url"]

            # Mock 模式不需要 API key
            if self.provider == "mock":
                api_key = api_key or "mock"

            # 创建AI客户端
            self.client = AIProviderFactory.create_client(
                provider=self.provider,
                api_key=api_key,
                model=model,
                base_url=base_url
            )
            self.model = self.client.model

            # 获取提供商名称用于显示
            provider_names = {
                "openai": "OpenAI GPT",
                "anthropic": "Anthropic Claude",
                "google": "Google Gemini",
                "deepseek": "DeepSeek",
                "qwen": "阿里云通义千问",
                "glm": "智谱AI (GLM)",
                "moonshot": "月之暗面 Kimi",
                "ernie": "百度文心一言",
                "minimax": "MiniMax",
                "doubao": "字节豆包",
                "ollama": "Ollama",
                "mock": "Mock"
            }
            provider_name = provider_names.get(self.provider, self.provider)

            if self.provider != "mock":
                print(f"使用 {provider_name}，模型: {self.model}")
            else:
                print("使用 Mock 模式进行三元组提取")

        except ValueError as e:
            print(f"警告: AI 配置错误 ({e})，将使用 mock 模式")
            self.provider = "mock"
            self.client = AIProviderFactory.create_client("mock")
            self.model = "mock"
        except (ConnectionError, TimeoutError, RuntimeError) as e:
            print(f"警告: 无法初始化 AI 客户端 ({e})，将使用 mock 模式")
            self.provider = "mock"
            self.client = AIProviderFactory.create_client("mock")
            self.model = "mock"
        except Exception as e:
            # 捕获其他未预期的异常，但不暴露详细信息
            print(f"警告: AI 客户端初始化时发生未知错误，将使用 mock 模式")
            self.provider = "mock"
            self.client = AIProviderFactory.create_client("mock")
            self.model = "mock"

    def extract(self, chunk: Chunk) -> List[Triplet]:
        """
        Extract triplets from a text chunk (支持多模态内容).

        Args:
            chunk: Text chunk to extract from

        Returns:
            List of Triplet objects
        """
        print(f"\n{'='*80}")
        print(f"[知识抽取] 开始处理文本块 (chunk_id: {chunk.chunk_id})")
        print(f"文本长度: {len(chunk.text)} 字符")
        print(f"文本预览: {chunk.text[:200]}...")
        
        # 检查是否为多模态内容
        chunk_type = chunk.meta.get("type", "text")
        if chunk_type != "text":
            print(f"[知识抽取] 检测到多模态内容类型: {chunk_type}")

        if not self.client or self.provider == "mock":
            print(f"[知识抽取] 使用 Mock 模式（未配置 AI 服务）")
            result = self._mock_extract(chunk)
            print(f"[知识抽取] Mock 模式提取结果: {len(result)} 个三元组")
            return result

        # 根据内容类型选择不同的 prompt
        if chunk_type == "table":
            prompt = self.prompt_manager.render(
                "triplet_extraction", "table",
                text=chunk.text,
                rows=chunk.meta.get('rows', 'N/A'),
                cols=chunk.meta.get('cols', 'N/A'),
                page=chunk.meta.get('page', 'N/A')
            )
        elif chunk_type == "figure":
            prompt = self.prompt_manager.render(
                "triplet_extraction", "figure",
                text=chunk.text,
                figure_type=chunk.meta.get('figure_type', 'unknown'),
                caption=chunk.meta.get('caption', 'N/A'),
                page=chunk.meta.get('page', 'N/A')
            )
        elif chunk_type == "equation":
            prompt = self.prompt_manager.render(
                "triplet_extraction", "equation",
                text=chunk.text,
                latex=chunk.meta.get('latex', 'N/A'),
                page=chunk.meta.get('page', 'N/A')
            )
        elif chunk_type == "code":
            prompt = self.prompt_manager.render(
                "triplet_extraction", "code",
                text=chunk.text,
                language=chunk.meta.get('language', 'unknown'),
                page=chunk.meta.get('page', 'N/A')
            )
        else:
            prompt = self.prompt_manager.render("triplet_extraction", "text", text=chunk.text)
        
        # 如果 Prompt 加载失败，使用默认硬编码 Prompt（向后兼容）
        if not prompt:
            print(f"[知识抽取] Prompt 文件加载失败，使用默认 Prompt")
            prompt = self._build_prompt(chunk.text)
        
        raw_content = None

        try:
            print(f"[AI请求] Provider: {self.provider}, Model: {self.model}")
            print(f"[AI请求] 发送请求到 AI 服务...")

            messages = [
                {
                    "role": "system",
                    "content": "You are a knowledge extraction expert. Extract subject-predicate-object triplets from the given content. Return only valid JSON array."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            raw_content = self.client.chat_completion(
                messages=messages,
                temperature=0.3,
                json_mode=True
            )
            print(f"[AI响应] 收到响应，长度: {len(raw_content)} 字符")
            print(f"[AI响应] 原始内容预览: {raw_content[:500]}...")

            result = json.loads(raw_content)
            raw_triplets = result.get("triplets", [])
            print(f"[AI响应] 解析到原始三元组数量: {len(raw_triplets)}")

            for idx, t in enumerate(raw_triplets[:5], 1):
                print(f"   [{idx}] {t.get('subject', 'N/A')} - {t.get('predicate', 'N/A')} - {t.get('object', 'N/A')} (置信度: {t.get('confidence', 0)})")
            if len(raw_triplets) > 5:
                print(f"   ... 还有 {len(raw_triplets) - 5} 个三元组")

            # 构建证据信息（包含多模态元数据）
            evidence = {
                "docId": chunk.doc_id,
                "chunkId": chunk.chunk_id,
                "page": chunk.meta.get("page"),
                "offset": chunk.meta.get("offset"),
                "text": chunk.text[:200],
                "chunkType": chunk_type
            }
            
            # 添加多模态特定的元数据
            if chunk_type == "table":
                evidence["rows"] = chunk.meta.get("rows")
                evidence["cols"] = chunk.meta.get("cols")
            elif chunk_type == "figure":
                evidence["figureType"] = chunk.meta.get("figure_type")
                evidence["caption"] = chunk.meta.get("caption")
            elif chunk_type == "equation":
                evidence["latex"] = chunk.meta.get("latex")
            elif chunk_type == "code":
                evidence["language"] = chunk.meta.get("language")

            triplets = [
                Triplet(
                    subject=t.get("subject", ""),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                    confidence=t.get("confidence", 0.8),
                    evidence=evidence,
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id
                )
                for t in raw_triplets
                if t.get("subject") and t.get("predicate") and t.get("object")
            ]

            filtered_count = len(raw_triplets) - len(triplets)
            if filtered_count > 0:
                print(f"[过滤] 过滤掉 {filtered_count} 个无效三元组（缺少必要字段）")

            print(f"[知识抽取] 成功提取 {len(triplets)} 个有效三元组")
            print(f"{'='*80}\n")

            return triplets
        except json.JSONDecodeError as e:
            print(f"[知识抽取] JSON 解析错误: {e}")
            if raw_content:
                print(f"[AI响应] 原始响应内容: {raw_content[:1000]}")
            return []
        except Exception as e:
            print(f"[知识抽取] 提取失败: {e}")
            import traceback
            print(f"[错误详情] {traceback.format_exc()}")
            return []

    def _build_prompt(self, text: str) -> str:
        """Build bilingual extraction prompt for both Chinese and English."""
        return f"""You are a professional knowledge graph construction expert. Extract structured knowledge triplets (subject-relation-object) from the given text.
你是一个专业的知识图谱构建专家。请从以下文本中提取结构化的知识三元组（主体-关系-客体）。

**Text Content / 文本内容：**
{text}

**Task Requirements / 任务要求：**
1. Identify core concepts, entities, and key information / 识别核心概念、实体和关键信息
2. Extract semantic relationships between them / 提取它们之间的语义关系
3. Perform structured organization and optimization / 进行结构化整理和优化
4. Ensure knowledge practicality and accuracy / 确保知识具有实用性和准确性
5. **Preserve original language**: Keep concepts in their original language (Chinese/English) / **保留原始语言**：保持概念的原始语言（中英文）

**Relationship Types Guide / 关系类型指南：**
- `is_a` / `定义为`: A is a type/kind of B / A 是 B 的一种/一类
- `contains` / `包含`: A contains B as a component / A 包含 B 作为组成部分
- `belongs_to` / `属于`: A belongs to category B / A 属于 B 类别
- `has_property` / `具有属性`: A has characteristic or attribute / A 具有某种特性或属性
- `used_for` / `用于`: A is used to achieve/accomplish B / A 用于实现/完成 B
- `affects` / `影响`: A affects B / A 对 B 产生影响
- `relates_to` / `关联`: A is related to B / A 与 B 存在关联
- `composed_of` / `由...组成`: A is composed of B / A 由 B 组成
- `produces` / `产生`: A produces/generates B / A 产生/生成 B
- `depends_on` / `依赖`: A depends on B / A 依赖于 B
- `causes` / `导致`: A causes B / A 导致 B
- `implements` / `实现`: A implements B / A 实现了 B
- `derived_from` / `派生自`: A is derived from B / A 派生自 B
- `similar_to` / `相似于`: A is similar to B / A 与 B 相似

**Output Format (Pure JSON) / 输出格式（纯 JSON）：**
{{
  "triplets": [
    {{
      "subject": "Concept/Entity Name",
      "predicate": "Relationship Type (use types from guide above)",
      "object": "Target Concept/Entity/Attribute Value",
      "confidence": 0.85,
      "language": "en" or "zh" or "mixed"
    }}
  ]
}}

**Important Notes / 注意事项：**
- Subject and object should be concise, standardized nouns or noun phrases / 主体和客体应该是简洁、规范的名词或名词短语
- Keep the original language of concepts (do NOT translate) / 保持概念的原始语言（不要翻译）
- Use English relationship type identifiers (e.g., "is_a", "contains") / 使用英文关系类型标识符
- Confidence should reflect knowledge certainty (0.0-1.0) / confidence 应反映知识确定程度（0.0-1.0）
- Give higher confidence to definitional, structural knowledge / 对定义性、结构性知识给予更高置信度
- Ignore trivial details, focus on core knowledge / 忽略无关细节，聚焦核心知识点
- If no clear knowledge in text, return empty array / 如果文本中没有明确知识点，返回空数组

Return ONLY the JSON object, no other explanatory text.
只返回 JSON 对象，不要包含任何其他文字说明。"""

    def _build_table_prompt(self, chunk: Chunk) -> str:
        """Build extraction prompt for table content."""
        return f"""You are a professional knowledge graph construction expert. Extract structured knowledge triplets from the given table content.
你是一位专业的知识图谱构建专家。请从以下表格内容中提取结构化的知识三元组。

**Table Content / 表格内容：**
{chunk.text}

**Table Metadata / 表格元数据：**
- Rows: {chunk.meta.get('rows', 'N/A')}
- Columns: {chunk.meta.get('cols', 'N/A')}
- Page: {chunk.meta.get('page', 'N/A')}

**Task Requirements / 任务要求：**
1. Analyze the table structure and extract key entities from headers and cells / 分析表格结构，从标题和单元格中提取关键实体
2. Identify semantic relationships between entities based on table data / 根据表格数据识别实体之间的语义关系
3. Extract comparison relationships, category mappings, and property-value pairs / 提取比较关系、类别映射和属性值对
4. **Preserve original language**: Keep concepts in their original language (Chinese/English) / **保留原始语言**

**Relationship Types Guide / 关系类型指南：**
- `is_a` / `定义为`: A is a type/kind of B / A 是 B 的一种/一类
- `contains` / `包含`: A contains B as a component / A 包含 B 作为组成部分
- `belongs_to` / `属于`: A belongs to category B / A 属于 B 类别
- `has_property` / `具有属性`: A has characteristic or attribute / A 具有某种特性或属性
- `used_for` / `用于`: A is used to achieve/accomplish B / A 用于实现/完成 B
- `affects` / `影响`: A affects B / A 对 B 产生影响
- `relates_to` / `关联`: A is related to B / A 与 B 存在关联
- `composed_of` / `由...组成`: A is composed of B / A 由 B 组成
- `produces` / `产生`: A produces/generates B / A 产生/生成 B
- `depends_on` / `依赖`: A depends on B / A 依赖于 B
- `causes` / `导致`: A causes B / A 导致 B
- `implements` / `实现`: A implements B / A 实现了 B
- `derived_from` / `派生自`: A is derived from B / A 派生自 B
- `similar_to` / `相似于`: A is similar to B / A 与 B 相似

**Output Format (Pure JSON) / 输出格式（纯 JSON）：**
{{
  "triplets": [
    {{
      "subject": "Entity/Concept Name",
      "predicate": "Relationship Type (use types from guide above)",
      "object": "Target Entity/Value",
      "confidence": 0.85,
      "language": "zh" or "en" or "mixed"
    }}
  ]
}}

**Important Notes / 注意事项：**
- Use only relationship types from the guide above / 仅使用上述关系类型
- Focus on extracting factual knowledge from table data / 专注于从表格数据中提取事实性知识
- Subject and object should be concise, standardized nouns / 主体和客体应该是简洁、规范的名词
- Return ONLY the JSON object, no other text."""

    def _build_figure_prompt(self, chunk: Chunk) -> str:
        """Build extraction prompt for figure/image content."""
        return f"""You are a professional knowledge graph construction expert. Extract structured knowledge triplets from the given figure description.
你是一位专业的知识图谱构建专家。请从以下图表描述中提取结构化的知识三元组。

**Figure Description / 图表描述：**
{chunk.text}

**Figure Metadata / 图表元数据：**
- Type: {chunk.meta.get('figure_type', 'unknown')}
- Caption: {chunk.meta.get('caption', 'N/A')}
- Page: {chunk.meta.get('page', 'N/A')}

**Task Requirements / 任务要求：**
1. Analyze the figure caption and description to identify main topics / 分析图表标题和描述，识别主题
2. Extract key concepts, metrics, and relationships presented / 提取关键概念、指标和关系
3. Identify entities being compared or analyzed / 识别正在比较或分析的实体
4. Extract trends, patterns, and conclusions / 提取趋势、模式和结论
5. **Preserve original language** / **保留原始语言**

**Relationship Types Guide / 关系类型指南：**
- `is_a` / `定义为`: A is a type/kind of B / A 是 B 的一种/一类
- `contains` / `包含`: A contains B as a component / A 包含 B 作为组成部分
- `belongs_to` / `属于`: A belongs to category B / A 属于 B 类别
- `has_property` / `具有属性`: A has characteristic or attribute / A 具有某种特性或属性
- `used_for` / `用于`: A is used to achieve/accomplish B / A 用于实现/完成 B
- `affects` / `影响`: A affects B / A 对 B 产生影响
- `relates_to` / `关联`: A is related to B / A 与 B 存在关联
- `composed_of` / `由...组成`: A is composed of B / A 由 B 组成
- `produces` / `产生`: A produces/generates B / A 产生/生成 B
- `depends_on` / `依赖`: A depends on B / A 依赖于 B
- `causes` / `导致`: A causes B / A 导致 B
- `implements` / `实现`: A implements B / A 实现了 B
- `derived_from` / `派生自`: A is derived from B / A 派生自 B
- `similar_to` / `相似于`: A is similar to B / A 与 B 相似

**Output Format (Pure JSON) / 输出格式（纯 JSON）：**
{{
  "triplets": [
    {{
      "subject": "Concept/Entity Name",
      "predicate": "Relationship Type (use types from guide above)",
      "object": "Target Concept/Entity/Value",
      "confidence": 0.85,
      "language": "zh" or "en" or "mixed"
    }}
  ]
}}

**Important Notes / 注意事项：**
- Use only relationship types from the guide above / 仅使用上述关系类型
- Focus on extracting the main message and relationships / 专注于提取主要信息和关系
- Subject and object should be concise, standardized nouns / 主体和客体应该是简洁、规范的名词
- Return ONLY the JSON object, no other text."""

    def _build_equation_prompt(self, chunk: Chunk) -> str:
        """Build extraction prompt for mathematical equations."""
        return f"""You are a professional knowledge graph construction expert. Extract structured knowledge triplets from the given mathematical equation.
你是一位专业的知识图谱构建专家。请从以下数学公式中提取结构化的知识三元组。

**Equation / 公式：**
{chunk.text}

**Equation Metadata / 公式元数据：**
- LaTeX: {chunk.meta.get('latex', 'N/A')}
- Page: {chunk.meta.get('page', 'N/A')}

**Task Requirements / 任务要求：**
1. Parse the mathematical formula to identify variables, constants, and operators / 解析数学公式，识别变量、常量和运算符
2. Extract semantic relationships between mathematical entities / 提取数学实体之间的语义关系
3. Identify the physical meaning or domain of the formula / 识别公式的物理意义或应用领域
4. Extract definitions and relationships between mathematical concepts / 提取数学概念之间的定义和关系
5. **Preserve original language and mathematical notation** / **保留原始语言和数学符号**

**Relationship Types Guide / 关系类型指南：**
- `is_a` / `定义为`: A is a type/kind of B / A 是 B 的一种/一类
- `contains` / `包含`: A contains B as a component / A 包含 B 作为组成部分
- `belongs_to` / `属于`: A belongs to category B / A 属于 B 类别
- `has_property` / `具有属性`: A has characteristic or attribute / A 具有某种特性或属性
- `used_for` / `用于`: A is used to achieve/accomplish B / A 用于实现/完成 B
- `affects` / `影响`: A affects B / A 对 B 产生影响
- `relates_to` / `关联`: A is related to B / A 与 B 存在关联
- `composed_of` / `由...组成`: A is composed of B / A 由 B 组成
- `produces` / `产生`: A produces/generates B / A 产生/生成 B
- `depends_on` / `依赖`: A depends on B / A 依赖于 B
- `causes` / `导致`: A causes B / A 导致 B
- `implements` / `实现`: A implements B / A 实现了 B
- `derived_from` / `派生自`: A is derived from B / A 派生自 B
- `similar_to` / `相似于`: A is similar to B / A 与 B 相似

**Output Format (Pure JSON) / 输出格式（纯 JSON）：**
{{
  "triplets": [
    {{
      "subject": "Variable/Concept Name",
      "predicate": "Relationship Type (use types from guide above)",
      "object": "Target Concept/Value",
      "confidence": 0.85,
      "language": "zh" or "en" or "mixed"
    }}
  ]
}}

**Important Notes / 注意事项：**
- Use only relationship types from the guide above / 仅使用上述关系类型
- Extract mathematical relationships accurately / 准确提取数学关系
- Preserve mathematical notation in subject/object / 在主体和客体中保留数学符号
- Return ONLY the JSON object, no other text."""

    def _build_code_prompt(self, chunk: Chunk) -> str:
        """Build extraction prompt for code blocks."""
        return f"""You are a professional knowledge graph construction expert. Extract structured knowledge triplets from the given source code.
你是一位专业的知识图谱构建专家。请从以下源代码中提取结构化的知识三元组。

**Code Content / 代码内容：**
{chunk.text}

**Code Metadata / 代码元数据：**
- Language: {chunk.meta.get('language', 'unknown')}
- Page: {chunk.meta.get('page', 'N/A')}

**Task Requirements / 任务要求：**
1. Analyze the code structure to identify classes, functions, and variables / 分析代码结构，识别类、函数和变量
2. Extract relationships between code elements / 提取代码元素之间的关系
3. Identify design patterns, algorithms, and data structures used / 识别使用的设计模式、算法和数据结构
4. Extract the purpose and functionality of the code / 提取代码的目的和功能
5. **Preserve original language and code syntax** / **保留原始语言和代码语法**

**Relationship Types Guide / 关系类型指南：**
- `is_a` / `定义为`: A is a type/kind of B / A 是 B 的一种/一类
- `contains` / `包含`: A contains B as a component / A 包含 B 作为组成部分
- `belongs_to` / `属于`: A belongs to category B / A 属于 B 类别
- `has_property` / `具有属性`: A has characteristic or attribute / A 具有某种特性或属性
- `used_for` / `用于`: A is used to achieve/accomplish B / A 用于实现/完成 B
- `affects` / `影响`: A affects B / A 对 B 产生影响
- `relates_to` / `关联`: A is related to B / A 与 B 存在关联
- `composed_of` / `由...组成`: A is composed of B / A 由 B 组成
- `produces` / `产生`: A produces/generates B / A 产生/生成 B
- `depends_on` / `依赖`: A depends on B / A 依赖于 B
- `causes` / `导致`: A causes B / A 导致 B
- `implements` / `实现`: A implements B / A 实现了 B
- `derived_from` / `派生自`: A is derived from B / A 派生自 B
- `similar_to` / `相似于`: A is similar to B / A 与 B 相似

**Output Format (Pure JSON) / 输出格式（纯 JSON）：**
{{
  "triplets": [
    {{
      "subject": "Code Element Name",
      "predicate": "Relationship Type (use types from guide above)",
      "object": "Related Element/Concept",
      "confidence": 0.85,
      "language": "zh" or "en" or "mixed"
    }}
  ]
}}

**Important Notes / 注意事项：**
- Use only relationship types from the guide above / 仅使用上述关系类型
- Extract technical relationships accurately / 准确提取技术关系
- Preserve code identifiers in subject/object / 在主体和客体中保留代码标识符
- Return ONLY the JSON object, no other text."""

    def _mock_extract(self, chunk: Chunk) -> List[Triplet]:
        """Mock extraction for testing (支持多模态内容)."""
        triplets = []
        text = chunk.text
        chunk_type = chunk.meta.get("type", "text")
        import re
        
        if chunk_type == "table":
            # 表格 Mock 提取：查找表格中的关系
            row_pattern = re.compile(r'\|([^|]+)\|([^|]+)\|')
            for match in row_pattern.finditer(text):
                subject = match.group(1).strip()
                obj = match.group(2).strip()
                if subject and obj and len(subject) > 2 and len(obj) > 2:
                    triplets.append(Triplet(
                        subject=subject,
                        predicate="has_property",
                        object=obj,
                        confidence=0.75,
                        evidence={
                            "docId": chunk.doc_id,
                            "chunkId": chunk.chunk_id,
                            "page": chunk.meta.get("page"),
                            "chunkType": "table",
                            "rows": chunk.meta.get("rows"),
                            "cols": chunk.meta.get("cols")
                        },
                        doc_id=chunk.doc_id,
                        chunk_id=chunk.chunk_id
                    ))
        
        elif chunk_type == "figure":
            # 图表 Mock 提取
            caption = chunk.meta.get("caption", "")
            if caption:
                triplets.append(Triplet(
                    subject=caption,
                    predicate="relates_to",
                    object="data visualization",
                    confidence=0.7,
                    evidence={
                        "docId": chunk.doc_id,
                        "chunkId": chunk.chunk_id,
                        "page": chunk.meta.get("page"),
                        "chunkType": "figure",
                        "figureType": chunk.meta.get("figure_type")
                    },
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id
                ))
        
        elif chunk_type == "equation":
            # 公式 Mock 提取
            latex = chunk.meta.get("latex", text)
            if latex:
                # 提取变量
                vars_pattern = re.compile(r'\\?([a-zA-Z]+)')
                matches = vars_pattern.findall(latex)[:3]
                for var in matches:
                    triplets.append(Triplet(
                        subject=var,
                        predicate="belongs_to",
                        object="mathematical formula",
                        confidence=0.75,
                        evidence={
                            "docId": chunk.doc_id,
                            "chunkId": chunk.chunk_id,
                            "page": chunk.meta.get("page"),
                            "chunkType": "equation",
                            "latex": latex
                        },
                        doc_id=chunk.doc_id,
                        chunk_id=chunk.chunk_id
                    ))
        
        elif chunk_type == "code":
            # 代码 Mock 提取
            language = chunk.meta.get("language", "unknown")
            # 查找函数定义
            func_pattern = re.compile(r'(def|function|class)\s+(\w+)')
            for match in func_pattern.finditer(text):
                func_name = match.group(2).strip()
                if func_name:
                    triplets.append(Triplet(
                        subject=func_name,
                        predicate="is_a",
                        object=f"{match.group(1)}",
                        confidence=0.7,
                        evidence={
                            "docId": chunk.doc_id,
                            "chunkId": chunk.chunk_id,
                            "page": chunk.meta.get("page"),
                            "chunkType": "code",
                            "language": language
                        },
                        doc_id=chunk.doc_id,
                        chunk_id=chunk.chunk_id
                    ))
        
        else:
            # 默认文本处理（原有逻辑）
            is_pattern = re.compile(r'([A-Z][a-zA-Z\s]+?)\s+is\s+(?:a\s+)?([a-zA-Z\s]+?)(?:\.|,|$)')
            for match in is_pattern.finditer(text):
                triplets.append(Triplet(
                    subject=match.group(1).strip(),
                    predicate="is_a",
                    object=match.group(2).strip(),
                    confidence=0.7,
                    evidence={
                        "docId": chunk.doc_id,
                        "chunkId": chunk.chunk_id,
                        "page": chunk.meta.get("page"),
                        "offset": chunk.meta.get("offset"),
                        "text": chunk.text[:200],
                        "chunkType": "text"
                    },
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id
                ))
        
        return triplets