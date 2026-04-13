"""AI Provider configuration and unified interface."""
from typing import Optional, Literal, List, Dict, Any
from openai import OpenAI
import anthropic
import json


# 支持的AI提供商类型
AIProviderType = Literal[
    "openai",           # OpenAI GPT
    "anthropic",        # Anthropic Claude
    "google",           # Google Gemini
    "grok",             # X Grok
    "deepseek",         # DeepSeek
    "qwen",             # 阿里云通义千问
    "glm",              # 智谱AI (GLM)
    "moonshot",         # 月之暗面 Kimi
    "ernie",            # 百度文心一言
    "minimax",          # MiniMax
    "doubao",           # 字节豆包
    "ollama",           # Ollama 本地模型
    "nvidia",           # NVIDIA NIM
    "modelscope",       # ModelScope
    "zhizengzeng",      # 智增增 AI
    "mock"              # Mock 模式（测试用）
]


class BaseAIClient:
    """Base AI client interface."""
    
    def __init__(self, model: str, **kwargs):
        self.model = model
        self.kwargs = kwargs
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        """
        Send chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            extra_params: Additional provider-specific parameters
            
        Returns:
            Response text content
        """
        raise NotImplementedError


class GrokClient(BaseAIClient):
    """X Grok client (via OpenAI-compatible API)."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        # X Grok 可以通过 OpenAI 兼容接口访问
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://api.x.ai/v1"
        )

    def chat_completion(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.3,
            **extra_params
    ) -> str:
        # 处理 json_mode 参数
        params = {k: v for k, v in extra_params.items() if k != "json_mode"}
        if extra_params.get("json_mode"):
            params["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                **params
            )
            return response.choices[0].message.content
        except Exception as e:
            # 提供更详细的错误信息
            error_msg = str(e)
            error_type = type(e).__name__

            # 获取实际的 base_url（从客户端对象）
            actual_base_url = getattr(self.client, 'base_url', 'unknown')

            if "404" in error_msg or "not found" in error_msg.lower() or error_type == "NotFoundError":
                raise ValueError(
                    f"API endpoint not found (404). "
                    f"Please check your base_url configuration. "
                    f"Current base_url: {actual_base_url}, "
                    f"Model: {self.model}. "
                    f"This usually means:\n"
                    f"  1. The base_url is incorrect or incomplete\n"
                    f"  2. The API endpoint path is wrong\n"
                    f"  3. The service is not available at the specified URL\n"
                    f"Original error: {error_msg}"
                ) from e
            raise


class OpenAIClient(BaseAIClient):
    """OpenAI GPT client."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"} if extra_params.get("json_mode") else None,
            **{k: v for k, v in extra_params.items() if k != "json_mode"}
        )
        return response.choices[0].message.content


class AnthropicClient(BaseAIClient):
    """Anthropic Claude client."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**kwargs)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # Anthropic 的 messages 格式稍有不同，需要分离 system 消息
        system_msg = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        # 如果请求 JSON 模式，在 system prompt 中添加要求
        if extra_params.get("json_mode"):
            json_instruction = "\n\n重要：请确保返回的内容是有效的 JSON 格式，不要包含任何额外的文本或说明。"
            if system_msg:
                system_msg = system_msg + json_instruction
            else:
                system_msg = json_instruction.strip()
        
        kwargs = {
            "model": self.model,
            "messages": user_messages,
            "temperature": temperature,
            "max_tokens": extra_params.get("max_tokens", 4096)
        }
        
        # 过滤掉 json_mode 参数
        kwargs = {k: v for k, v in kwargs.items() if k != "json_mode"}
        
        if system_msg:
            kwargs["system"] = system_msg
        
        response = self.client.messages.create(**kwargs)
        return response.content[0].text


class GoogleGeminiClient(BaseAIClient):
    """Google Gemini client (via OpenAI-compatible API)."""
    
    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None):
        super().__init__(model)
        # Google Gemini 可以通过 OpenAI 兼容接口访问
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta/openai/"
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 处理 json_mode 参数
        params = {k: v for k, v in extra_params.items() if k != "json_mode"}
        if extra_params.get("json_mode"):
            params["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            **params
        )
        return response.choices[0].message.content


class OpenAICompatibleClient(BaseAIClient):
    """
    Generic OpenAI-compatible client for providers like:
    - DeepSeek
    - 通义千问 (Qwen)
    - 智谱AI (GLM)
    - Moonshot (Kimi)
    - 文心一言 (ERNIE)
    - MiniMax
    - 豆包 (Doubao)
    - Ollama
    """
    
    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(model)
        # 规范化 base_url：移除末尾斜杠（除非是 Google 的特殊情况）
        normalized_base_url = base_url.rstrip('/') if not base_url.endswith('/openai/') else base_url
        
        # 特殊处理：Ollama 需要 /v1 后缀
        # 如果 base_url 是 localhost:11434 且没有 /v1，自动添加
        if ':11434' in normalized_base_url and not normalized_base_url.endswith('/v1'):
            normalized_base_url = normalized_base_url + '/v1'
            print(f"⚠️  [AI客户端] 检测到 Ollama base_url，已自动添加 /v1 后缀")
        
        # 验证 base_url 格式
        if not normalized_base_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid base_url format: {base_url}. Must start with http:// or https://")
        
        print(f"[AI客户端] 初始化 OpenAI 兼容客户端")
        print(f"   Model: {model}")
        print(f"   Base URL: {normalized_base_url}")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=normalized_base_url
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 处理 json_mode 参数
        params = {k: v for k, v in extra_params.items() if k != "json_mode"}
        if extra_params.get("json_mode"):
            params["response_format"] = {"type": "json_object"}
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                **params
            )
            return response.choices[0].message.content
        except Exception as e:
            # 提供更详细的错误信息
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 获取实际的 base_url（从客户端对象）
            actual_base_url = getattr(self.client, 'base_url', 'unknown')
            
            if "404" in error_msg or "not found" in error_msg.lower() or error_type == "NotFoundError":
                raise ValueError(
                    f"API endpoint not found (404). "
                    f"Please check your base_url configuration. "
                    f"Current base_url: {actual_base_url}, "
                    f"Model: {self.model}. "
                    f"This usually means:\n"
                    f"  1. The base_url is incorrect or incomplete\n"
                    f"  2. The API endpoint path is wrong\n"
                    f"  3. The service is not available at the specified URL\n"
                    f"Original error: {error_msg}"
                ) from e
            raise


class MockClient(BaseAIClient):
    """Mock client for testing."""
    
    def __init__(self):
        super().__init__("mock")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        # 检查是否是指代消解请求（通过 prompt 内容判断）
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 如果是指代消解请求（包含"指代消解"关键词）
        if "指代消解" in user_message or "mention" in user_message.lower():
            # 尝试从 prompt 中提取提及信息
            import re
            # 简单的 mock 响应：假设第一个提及匹配第一个候选先行词
            resolutions = []
            mention_matches = re.findall(r'"mention_text":\s*"([^"]+)"', user_message)
            candidate_matches = re.findall(r'"text":\s*"([^"]+)"', user_message)
            
            # 如果有提及和候选，创建简单的映射
            if mention_matches and candidate_matches:
                for i, mention_text in enumerate(mention_matches[:3]):  # 最多处理前3个
                    if i < len(candidate_matches):
                        resolutions.append({
                            "mention_id": i + 1,
                            "mention_text": mention_text,
                            "antecedent_text": candidate_matches[0],  # 简单映射到第一个候选
                            "confidence": 0.8,
                            "rationale": "Mock 模式：自动映射"
                        })
            
            # 如果没有提取到，返回一个默认响应
            if not resolutions:
                resolutions = [{
                    "mention_id": 1,
                    "mention_text": "它",
                    "antecedent_text": "示例实体",
                    "confidence": 0.7,
                    "rationale": "Mock 模式：默认响应"
                }]
            
            return json.dumps({
                "resolutions": resolutions,
                "resolved_text": None  # Mock 模式不生成替换文本
            }, ensure_ascii=False)
        
        # 默认返回实体抽取格式（向后兼容）
        return json.dumps({
            "triplets": [
                {
                    "subject": "示例主体",
                    "predicate": "relates_to",
                    "object": "示例客体",
                    "confidence": 0.5,
                    "language": "zh"
                }
            ]
        }, ensure_ascii=False)


class AIProviderFactory:
    """Factory for creating AI clients."""
    
    # 默认的 base_url 配置
    # 注意：base_url 不应以斜杠结尾（除了 Google 的特殊情况）
    DEFAULT_BASE_URLS = {
        "openai": None,  # 使用默认
        "anthropic": None,
        "google": "https://generativelanguage.googleapis.com/v1beta/openai/",  # Google 需要末尾斜杠
        "grok": "https://api.x.ai/v1",  # X Grok API
        "deepseek": "https://api.deepseek.com/v1",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "moonshot": "https://api.moonshot.cn/v1",
        "ernie": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop",  # 文心一言 API
        "minimax": "https://api.minimax.chat/v1",
        "doubao": "https://ark.cn-beijing.volces.com/api/v3",
        "ollama": "http://localhost:11434/v1",
        "nvidia": "https://integrate.api.nvidia.com/v1",
        "modelscope": "https://api-inference.modelscope.cn/v1",
        "zhizengzeng": "https://api.zhizengzeng.com/v1"
    }
    
    # 默认模型配置
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-sonnet-20241022",
        "google": "gemini-2.0-flash-exp",
        "grok": "grok-2-1212",  # X Grok 默认模型
        "deepseek": "deepseek-chat",
        "qwen": "qwen-plus",
        "glm": "glm-4-flash",
        "moonshot": "moonshot-v1-8k",
        "ernie": "ernie-4.0-8k-latest",
        "minimax": "abab6.5s-chat",
        "doubao": "doubao-pro-4k",
        "ollama": "llama3",
        "nvidia": "MiniMax/MiniMax-M2.5",
        "modelscope": "MiniMax/MiniMax-M2.5",
        "zhizengzeng": "qwen3-max",
        "mock": "mock"
    }
    
    @classmethod
    def create_client(
        cls,
        provider: AIProviderType,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> BaseAIClient:
        """
        Create AI client based on provider type.
        
        Args:
            provider: AI provider type
            api_key: API key (not needed for mock/ollama)
            model: Model name (use default if not provided)
            base_url: Custom base URL (use default if not provided)
            
        Returns:
            AI client instance
            
        Raises:
            ValueError: If provider is not supported or missing required config
        """
        # 使用默认模型和base_url（如果未提供）
        model = model or cls.DEFAULT_MODELS.get(provider)
        base_url = base_url or cls.DEFAULT_BASE_URLS.get(provider)
        
        if provider == "mock":
            return MockClient()
        
        if provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required")
            return OpenAIClient(api_key, model, base_url)
        
        if provider == "anthropic":
            if not api_key:
                raise ValueError("Anthropic API key is required")
            return AnthropicClient(api_key, model, base_url)
        
        if provider == "google":
            if not api_key:
                raise ValueError("Google API key is required")
            return GoogleGeminiClient(api_key, model, base_url)

        if provider == "grok":
            if not api_key:
                raise ValueError("X Grok API key is required")
            return GrokClient(api_key, model, base_url)
        
        # 其他所有 OpenAI 兼容的提供商
        if provider in ["deepseek", "qwen", "glm", "moonshot", "ernie", "minimax", "doubao", "ollama", "nvidia", "modelscope", "zhizengzeng"]:
            # Ollama 不需要真实的 API key
            if provider == "ollama":
                api_key = api_key or "ollama"
            elif not api_key:
                raise ValueError(f"{provider} API key is required")
            
            return OpenAICompatibleClient(api_key, model, base_url)
        
        raise ValueError(f"Unsupported AI provider: {provider}")
    
    @classmethod
    def get_provider_info(cls, provider: AIProviderType) -> Dict[str, Any]:
        """Get provider information including default model and base URL."""
        return {
            "provider": provider,
            "default_model": cls.DEFAULT_MODELS.get(provider),
            "default_base_url": cls.DEFAULT_BASE_URLS.get(provider)
        }
    
    @classmethod
    def list_providers(cls) -> List[Dict[str, Any]]:
        """List all supported providers with their default configurations."""
        return [
            {
                "id": "openai",
                "name": "OpenAI GPT",
                "default_model": cls.DEFAULT_MODELS["openai"],
                "requires_api_key": True
            },
            {
                "id": "anthropic",
                "name": "Anthropic Claude",
                "default_model": cls.DEFAULT_MODELS["anthropic"],
                "requires_api_key": True
            },
            {
                "id": "google",
                "name": "Google Gemini",
                "default_model": cls.DEFAULT_MODELS["google"],
                "requires_api_key": True
            },
            {
                "id": "grok",
                "name": "X Grok",
                "default_model": cls.DEFAULT_MODELS["grok"],
                "requires_api_key": True
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "default_model": cls.DEFAULT_MODELS["deepseek"],
                "requires_api_key": True
            },
            {
                "id": "qwen",
                "name": "阿里云通义千问",
                "default_model": cls.DEFAULT_MODELS["qwen"],
                "requires_api_key": True
            },
            {
                "id": "glm",
                "name": "智谱AI (GLM)",
                "default_model": cls.DEFAULT_MODELS["glm"],
                "requires_api_key": True
            },
            {
                "id": "moonshot",
                "name": "月之暗面 Kimi",
                "default_model": cls.DEFAULT_MODELS["moonshot"],
                "requires_api_key": True
            },
            {
                "id": "ernie",
                "name": "百度文心一言",
                "default_model": cls.DEFAULT_MODELS["ernie"],
                "requires_api_key": True
            },
            {
                "id": "minimax",
                "name": "MiniMax",
                "default_model": cls.DEFAULT_MODELS["minimax"],
                "requires_api_key": True
            },
            {
                "id": "doubao",
                "name": "字节豆包",
                "default_model": cls.DEFAULT_MODELS["doubao"],
                "requires_api_key": True
            },
            {
                "id": "ollama",
                "name": "Ollama",
                "default_model": cls.DEFAULT_MODELS["ollama"],
                "requires_api_key": False
            },
            {
                "id": "nvidia",
                "name": "NVIDIA NIM",
                "default_model": cls.DEFAULT_MODELS["nvidia"],
                "requires_api_key": True
            },
            {
                "id": "modelscope",
                "name": "ModelScope",
                "default_model": cls.DEFAULT_MODELS["modelscope"],
                "requires_api_key": True
            },
            {
                "id": "zhizengzeng",
                "name": "ZhiZengZeng",
                "default_model": cls.DEFAULT_MODELS["zhizengzeng"],
                "requires_api_key": True
            },
            {
                "id": "mock",
                "name": "Mock (测试模式)",
                "default_model": "mock",
                "requires_api_key": False
            }
        ]


def get_ai_client(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> Optional[BaseAIClient]:
    """
    Factory function to get AI client based on provider.
    
    Args:
        provider: AI provider name (openai, qwen, anthropic, etc.)
        api_key: API key for the provider
        model: Model name (uses provider default if not specified)
        base_url: Custom API base URL (optional)
        
    Returns:
        AI client instance or None if mock mode
    """
    # Default models for each provider
    default_models = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-sonnet-20240229",
        "google": "gemini-1.5-pro",
        "grok": "grok-2-1212",
        "qwen": "qwen-max",
        "glm": "glm-4",
        "deepseek": "deepseek-chat",
        "moonshot": "moonshot-v1-auto",
        "ernie": "ernie-4.0-turbo-latest",
        "minimax": "abab6.5s-chat",
        "doubao": "doubao-pro-32k",
        "ollama": "llama2",
        "modelscope": "MiniMax/MiniMax-M2.5",
        "nvidia": "MiniMax/MiniMax-M2.5",
        "zhizengzeng": "qwen3-max",
        "mock": "mock"
    }
    
    # Use default model if not specified
    if not model:
        model = default_models.get(provider, "default")
    
    # Provider-specific client initialization
    if provider == "openai":
        if not api_key:
            raise ValueError("OpenAI requires api_key")
        return OpenAIClient(api_key=api_key, model=model, base_url=base_url)
    
    elif provider == "anthropic":
        if not api_key:
            raise ValueError("Anthropic Claude requires api_key")
        return AnthropicClient(api_key=api_key, model=model, base_url=base_url)
    
    elif provider == "google":
        if not api_key:
            raise ValueError("Google Gemini requires api_key")
        return GoogleGeminiClient(api_key=api_key, model=model, base_url=base_url)

    elif provider == "google":
        if not api_key:
            raise ValueError("Google Gemini requires api_key")
        return GoogleGeminiClient(api_key=api_key, model=model, base_url=base_url)
    
    elif provider in ["qwen", "glm", "deepseek", "moonshot", "ernie", "minimax", "doubao", "ollama", "modelscope", "zhizengzeng", "nvidia"]:
        if provider != "ollama" and not api_key:
            raise ValueError(f"{provider} requires api_key")
        # All these use OpenAI-compatible interface
        if not base_url:
            # Default base URLs for common providers
            base_urls = {
                "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "glm": "https://open.bigmodel.cn/api/paas/v4",
                "deepseek": "https://api.deepseek.com",
                "moonshot": "https://api.moonshot.cn/v1",
                "ernie": "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat",
                "minimax": "https://api.minimaxi.chat/v1",
                "doubao": "https://ark.cn-beijing.volces.com/api/v3",
                "ollama": "http://localhost:11434/v1",
                "modelscope": "https://api-inference.modelscope.cn/v1",
                "nvidia": "https://integrate.api.nvidia.com/v1",
                "zhizengzeng": "https://api.zhizengzeng.com/v1"
            }
            base_url = base_urls.get(provider)
        return OpenAICompatibleClient(api_key=api_key or "dummy", model=model, base_url=base_url)
    
    elif provider == "mock":
        # Mock client for testing - just returns predefined responses
        return MockAIClient(model=model)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


class MockAIClient(BaseAIClient):
    """Mock AI client for testing without API calls."""
    
    def __init__(self, model: str = "mock"):
        super().__init__(model)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        **extra_params
    ) -> str:
        """Return mock responses for testing."""
        # Extract user message
        user_message = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
        
        # Generate mock response based on question
        if "知识图谱" in user_message or "graph" in user_message.lower():
            return """知识图谱是一种以图形结构表示知识的方法，它通过节点（实体）和边（关系）来组织和展示知识。

**主要特点：**
- **节点**：代表实体（人物、地点、概念等）
- **边**：表示实体之间的关系
- **应用**：搜索、推荐系统、自然语言处理

知识图谱广泛应用于Google搜索、维基百科等大型应用中。"""
        
        elif "人工智能" in user_message or "AI" in user_message:
            return """人工智能（AI）是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的机器。

**主要领域：**
- 机器学习
- 深度学习
- 自然语言处理
- 计算机视觉

人工智能已经成为现代社会的重要技术。"""
        
        else:
            return f"""这是一个Mock模式的测试回答。

您的问题是: {user_message[:100]}

在实际应用中，这里会返回由AI模型生成的真实答案，同时配合知识图谱中的相关信息。"""
