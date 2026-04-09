"""Web search module for CRAG knowledge correction."""
import httpx
from typing import List, Dict, Any
from infra.config import Settings


class WebSearchService:
    """Service for web search functionality."""
    
    def __init__(self):
        self.settings = Settings()
        self.search_api = self.settings.web_search_api
        self.search_api_key = self.settings.web_search_api_key
        
    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Perform web search to get additional information.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of search results with title, snippet, and URL
        """
        try:
            # 使用SerpAPI或其他搜索API
            # 这里使用模拟实现，实际项目中需要替换为真实的搜索API
            print(f"🔍 [Web Search] 搜索查询: {query}")
            
            # 模拟搜索结果
            mock_results = [
                {
                    "title": f"{query} - 软件工程百科",
                    "snippet": f"{query}是软件工程中的重要概念，...",
                    "url": f"https://example.com/{query.replace(' ', '_')}"
                },
                {
                    "title": f"{query}的最佳实践",
                    "snippet": f"在软件工程中，{query}的最佳实践包括...",
                    "url": f"https://example.com/{query}_best_practices"
                },
                {
                    "title": f"{query}的实现方法",
                    "snippet": f"实现{query}的步骤包括...",
                    "url": f"https://example.com/implementing_{query}"
                }
            ]
            
            return mock_results[:limit]
            
        except Exception as e:
            print(f"❌ [Web Search] 搜索失败: {e}")
            return []
    
    def get_relevant_information(self, query: str, context: str) -> str:
        """
        Get relevant information from web search results.
        
        Args:
            query: Original question
            context: Current knowledge graph context
            
        Returns:
            Formatted web search results as string
        """
        search_results = self.search(query)
        
        if not search_results:
            return ""
        
        # 格式化搜索结果
        formatted_results = []
        for i, result in enumerate(search_results, 1):
            result_str = f"【网络搜索结果 {i}】\n"
            result_str += f"标题: {result.get('title', 'Unknown')}\n"
            result_str += f"摘要: {result.get('snippet', 'No snippet available')}\n"
            result_str += f"链接: {result.get('url', 'No URL')}\n"
            formatted_results.append(result_str)
        
        return "\n\n".join(formatted_results)


# 全局Web搜索服务实例
web_search_service = WebSearchService()