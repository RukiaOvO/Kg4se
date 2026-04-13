from pathlib import Path
from typing import Dict, Optional


class PromptManager:
    """Prompt 集中管理器"""
    
    def __init__(self):
        self.prompts: Dict[str, Dict[str, str]] = {}
        self._load_all_prompts()
    
    def _load_all_prompts(self):
        """加载所有 Prompt 文件"""
        prompts_dir = Path(__file__).parent
        
        for category_dir in prompts_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('_'):
                category = category_dir.name
                self.prompts[category] = {}
                
                for prompt_file in category_dir.iterdir():
                    if prompt_file.suffix == ".txt":
                        name = prompt_file.stem
                        try:
                            with open(prompt_file, "r", encoding="utf-8") as f:
                                self.prompts[category][name] = f.read()
                        except Exception as e:
                            print(f"[PromptManager] 加载 {prompt_file} 失败: {e}")
    
    def get(self, category: str, name: str) -> str:
        """获取指定 Prompt"""
        return self.prompts.get(category, {}).get(name, "")
    
    def render(self, category: str, name: str, **kwargs) -> str:
        """获取并渲染 Prompt（支持模板变量替换）"""
        template = self.get(category, name)
        if template:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                print(f"[PromptManager] 模板变量缺失: {e}")
                return template
        return ""
    
    def list_categories(self) -> list:
        """列出所有类别"""
        return list(self.prompts.keys())
    
    def list_prompts(self, category: str) -> list:
        """列出指定类别的所有 Prompt"""
        return list(self.prompts.get(category, {}).keys())


# 创建全局实例
prompt_manager = PromptManager()
