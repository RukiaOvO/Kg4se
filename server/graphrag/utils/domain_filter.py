"""
领域过滤器 (Domain Filter)

用于筛选软件工程领域相关的知识点，过滤无关实体和关系。
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("graphrag.domain_filter")

# 软件工程领域的核心关键词
SOFTWARE_ENGINEERING_KEYWORDS = {
    # 设计模式
    "singleton", "factory", "observer", "strategy", "adapter", "decorator",
    "proxy", "facade", "builder", "prototype", "abstract factory",
    "bridge", "composite", "flyweight", "template method", "chain of responsibility",
    "command", "interpreter", "iterator", "mediator", "memento",
    "state", "visitor", "mvc", "mvp", "mvvm",
    "单例", "工厂", "观察者", "策略", "适配器", "装饰", "代理", "外观",
    "建造者", "原型", "抽象工厂", "桥接", "组合", "享元", "模板方法",
    "责任链", "命令", "解释器", "迭代器", "中介者", "备忘录", "状态", "访问者",
    
    # 数据结构
    "array", "list", "stack", "queue", "tree", "graph", "heap", "hash table",
    "linkedlist", "binary tree", "avl tree", "red-black tree", "btree",
    "trie", "segment tree", "fenwick tree", "union-find",
    "数组", "链表", "栈", "队列", "树", "图", "堆", "哈希表",
    "二叉树", "avl树", "红黑树", "b树", "字典树", "线段树", "树状数组", "并查集",
    
    # 算法
    "sorting", "searching", "dynamic programming", "greedy", "backtracking",
    "divide and conquer", "recursion", "iteration", "bfs", "dfs",
    "dijkstra", "floyd-warshall", "bellman-ford", "kruskal", "prim",
    "排序", "搜索", "动态规划", "贪心", "回溯", "分治", "递归", "迭代",
    "广度优先", "深度优先", "最短路径", "最小生成树",
    
    # 面向对象
    "object-oriented", "inheritance", "polymorphism", "encapsulation",
    "abstraction", "interface", "abstract class", "overloading", "overriding",
    "面向对象", "继承", "多态", "封装", "抽象", "接口", "抽象类",
    "重载", "重写", "this", "super",
    
    # 编程范型
    "functional programming", "imperative", "declarative", "procedural",
    "reactive programming", "event-driven", "aspect-oriented",
    "函数式编程", "命令式", "声明式", "过程式", "响应式编程",
    "事件驱动", "面向切面",
    
    # 代码质量
    "refactoring", "clean code", "code smell", "technical debt",
    "maintainability", "readability", "testability", "performance optimization",
    "memory management", "garbage collection",
    "重构", "清洁代码", "代码异味", "技术债", "可维护性", "可读性",
    "可测试性", "性能优化", "内存管理", "垃圾回收",
    
    # 测试
    "unit test", "integration test", "system test", "acceptance test",
    "tdd", "bdd", "mock", "stub", "test case", "test suite",
    "coverage", "regression test", "smoke test",
    "单元测试", "集成测试", "系统测试", "验收测试",
    "测试驱动开发", "行为驱动开发", "模拟", "存根", "测试用例",
    "测试套件", "覆盖率", "回归测试", "冒烟测试",
    
    # 架构
    "architecture", "microservices", "monolithic", "layered",
    "event-driven architecture", "service-oriented architecture",
    "api gateway", "load balancer", "distributed system",
    "architecture pattern", "enterprise architecture",
    "架构", "微服务", "单体", "分层", "事件驱动架构", "面向服务架构",
    "api网关", "负载均衡", "分布式系统", "架构模式", "企业架构",
    
    # 并发与并行
    "concurrency", "parallelism", "thread", "process", "coroutine",
    "mutex", "semaphore", "lock", "atomic", "deadlock", "race condition",
    "synchronization", "thread pool", "async", "await", "promise",
    "并发", "并行", "线程", "进程", "协程", "互斥锁", "信号量",
    "原子操作", "死锁", "竞态条件", "同步", "线程池",
    
    # 数据库
    "database", "sql", "nosql", "relational", "document", "key-value",
    "transaction", "acid", "index", "query optimization", "normalization",
    "denormalization", "join", "aggregate", "schema",
    "数据库", "sql", "nosql", "关系数据库", "文档数据库",
    "事务", "酸特性", "索引", "查询优化", "范式化",
    
    # 安全
    "security", "authentication", "authorization", "encryption", "hashing",
    "sql injection", "xss", "csrf", "ssl/tls", "https",
    "access control", "privilege escalation", "vulnerability",
    "安全", "认证", "授权", "加密", "哈希", "sql注入",
    "访问控制", "权限提升", "漏洞",
    
    # 版本控制
    "git", "svn", "version control", "commit", "branch", "merge",
    "pull request", "merge conflict", "rebase", "cherry-pick",
    "版本控制", "提交", "分支", "合并", "拉取请求", "合并冲突",
    
    # 构建与部署
    "build", "deployment", "ci/cd", "continuous integration",
    "continuous deployment", "devops", "docker", "kubernetes",
    "container", "orchestration", "pipeline", "artifact",
    "构建", "部署", "持续集成", "持续部署", "容器", "编排", "流水线",
    
    # 文档与通信
    "documentation", "comment", "readme", "api documentation",
    "javadoc", "docstring", "wiki", "knowledge base",
    "文档", "注释", "readme", "api文档", "wiki", "知识库",
    
    # 其他常见术语
    "software", "code", "development", "programming", "debugging",
    "profiling", "logging", "monitoring", "metric", "analysis",
    "pattern", "principle", "best practice", "convention",
    "软件", "代码", "开发", "编程", "调试", "日志", "监控",
    "度量", "分析", "原则", "最佳实践", "约定",
}

# 排除的通用词
EXCLUDED_KEYWORDS = {
    "the", "a", "an", "and", "or", "not", "is", "are", "was", "were",
    "but", "be", "to", "of", "in", "on", "at", "by", "for", "with",
    "这", "那", "是", "和", "或", "非", "的", "了", "在", "有", "个",
    "什么", "什么样", "如何", "为什么", "怎样", "哪些", "哪个",
    "can", "could", "may", "might", "must", "should", "would", "will",
    "能", "可能", "必须", "应该", "会", "将",
    "person", "people", "thing", "way", "time", "year", "time",
    "数字", "符号", "特殊", "未知", "其他", "等等",
}

# 需要过滤的实体类型前缀
FILTERED_ENTITY_PATTERNS = [
    r"^(Mr\.|Mrs\.|Ms\.|Prof\.|Dr\.)",  # 称号前缀
    r"^[A-Z][a-z]+\s[A-Z][a-z]+$",      # 人名模式 (FirstName LastName)
    r"^\d{4}-\d{2}-\d{2}$",              # 日期模式
    r"^https?://",                       # URL
    r"^[a-z0-9_.+-]+@[a-z0-9-]+\.[a-z0-9-.]+$",  # Email
]


class DomainFilter:
    """
    领域过滤器
    
    过滤软件工程领域无关的实体和关系
    """
    
    def __init__(self):
        self.keywords = SOFTWARE_ENGINEERING_KEYWORDS
        self.excluded = EXCLUDED_KEYWORDS
        logger.info("DomainFilter initialized")
    
    def is_software_engineering_entity(self, entity_name: str, entity_type: str = "general") -> Tuple[bool, float]:
        """
        判断实体是否属于软件工程领域
        
        Args:
            entity_name: 实体名称
            entity_type: 实体类型 (e.g., "KnowledgePoint", "Concept")
        
        Returns:
            (是否相关, 置信度)
        """
        if not entity_name or len(entity_name.strip()) == 0:
            return False, 0.0
        
        entity_lower = entity_name.lower().strip()
        
        # 1. 检查是否匹配排除模式
        for pattern in FILTERED_ENTITY_PATTERNS:
            if re.match(pattern, entity_name):
                logger.debug(f"实体 '{entity_name}' 匹配排除模式: {pattern}")
                return False, 0.0
        
        # 2. 检查是否为排除词
        if entity_lower in self.excluded:
            return False, 0.0
        
        # 3. 计算关键词匹配分数
        words = re.split(r'[\s\-_,、，；;]', entity_lower)
        matched_keywords = 0
        total_meaningful_words = 0
        
        for word in words:
            word = word.strip()
            if len(word) < 2 or word in self.excluded:
                continue
            
            total_meaningful_words += 1
            
            # 精确匹配
            if word in self.keywords:
                matched_keywords += 1
            # 子串匹配
            elif any(keyword in word or word in keyword for keyword in self.keywords):
                matched_keywords += 0.5
        
        if total_meaningful_words == 0:
            # 没有有意义的词，返回 False
            return False, 0.0
        
        confidence = matched_keywords / total_meaningful_words
        
        # 4. 置信度阈值
        if confidence >= 0.3:
            return True, min(confidence, 1.0)
        else:
            logger.debug(f"实体 '{entity_name}' 置信度不足 ({confidence:.2f})")
            return False, confidence
    
    def is_valid_relationship(
        self,
        source_entity: str,
        target_entity: str,
        relationship_type: str,
        source_type: str = "KnowledgePoint",
        target_type: str = "KnowledgePoint"
    ) -> Tuple[bool, float]:
        """
        判断关系是否有效（仅允许5种关系）
        
        Args:
            source_entity: 源实体名称
            target_entity: 目标实体名称
            relationship_type: 关系类型
            source_type: 源实体类型
            target_type: 目标实体类型
        
        Returns:
            (是否有效, 置信度)
        """
        # 1. 检查关系类型是否允许
        allowed_relationships = {
            "BELONGS_TO",    # KnowledgePoint -> KnowledgePoint
            "FROM",          # KnowledgePoint -> Document
            "PRACTICES_IS",  # Question -> KnowledgePoint
            "HAS_TIMESTAMP", # Document -> Timestamp
            "IS"             # KnowledgePoint -> Content
        }
        
        if relationship_type not in allowed_relationships:
            logger.debug(f"关系类型 '{relationship_type}' 不在允许列表中")
            return False, 0.0
        
        # 2. 检查类型约束
        type_constraints = {
            "BELONGS_TO": (["KnowledgePoint"], ["KnowledgePoint"]),
            "FROM": (["KnowledgePoint"], ["Document"]),
            "PRACTICES_IS": (["Question"], ["KnowledgePoint"]),
            "HAS_TIMESTAMP": (["Document"], ["Timestamp"]),
            "IS": (["KnowledgePoint"], ["Content"])
        }
        
        if relationship_type in type_constraints:
            allowed_sources, allowed_targets = type_constraints[relationship_type]
            if source_type not in allowed_sources or target_type not in allowed_targets:
                logger.debug(
                    f"类型约束不匹配: {source_type}-{relationship_type}-{target_type} "
                    f"(expected: {allowed_sources}-{relationship_type}-{allowed_targets})"
                )
                return False, 0.0
        
        # 3. 检查实体本身是否相关（针对非Timestamp/Document实体）
        if source_type in ["KnowledgePoint", "Question"]:
            is_valid, conf = self.is_software_engineering_entity(source_entity, source_type)
            if not is_valid and conf < 0.2:
                return False, 0.0
        
        if target_type in ["KnowledgePoint", "Content", "Question"]:
            is_valid, conf = self.is_software_engineering_entity(target_entity, target_type)
            if not is_valid and conf < 0.2:
                return False, 0.0
        
        return True, 1.0
    
    def filter_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤实体列表，仅保留软件工程领域相关实体
        
        Args:
            entities: 实体列表 [{"name": ..., "type": ..., ...}, ...]
        
        Returns:
            过滤后的实体列表
        """
        filtered = []
        
        for entity in entities:
            entity_name = entity.get("name", "")
            entity_type = entity.get("type", "KnowledgePoint")
            
            # 对于Document, Timestamp, Content等类型，不进行过滤
            if entity_type in ["Document", "Timestamp", "Content"]:
                filtered.append(entity)
                continue
            
            # 对于KnowledgePoint, Question等，进行领域检查
            is_valid, confidence = self.is_software_engineering_entity(entity_name, entity_type)
            
            if is_valid:
                entity["domain_confidence"] = confidence
                filtered.append(entity)
                logger.debug(f"保留实体: {entity_name} (类型: {entity_type}, 置信度: {confidence:.2f})")
            else:
                logger.debug(f"过滤实体: {entity_name} (类型: {entity_type})")
        
        logger.info(f"实体过滤: {len(entities)} -> {len(filtered)}")
        return filtered
    
    def filter_relationships(
        self,
        relationships: List[Dict[str, Any]],
        entities: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        过滤关系列表，仅保留允许的5种关系
        
        Args:
            relationships: 关系列表
            entities: 实体字典 {entity_id: {name, type, ...}, ...}
        
        Returns:
            过滤后的关系列表
        """
        filtered = []
        
        for rel in relationships:
            rel_type = rel.get("type", "")
            source_id = rel.get("source", "")
            target_id = rel.get("target", "")
            
            source_entity = entities.get(source_id, {})
            target_entity = entities.get(target_id, {})
            
            source_name = source_entity.get("name", "")
            source_type = source_entity.get("type", "KnowledgePoint")
            target_name = target_entity.get("name", "")
            target_type = target_entity.get("type", "KnowledgePoint")
            
            is_valid, confidence = self.is_valid_relationship(
                source_entity=source_name,
                target_entity=target_name,
                relationship_type=rel_type,
                source_type=source_type,
                target_type=target_type
            )
            
            if is_valid:
                rel["domain_confidence"] = confidence
                filtered.append(rel)
                logger.debug(f"保留关系: {source_name} -[{rel_type}]-> {target_name}")
            else:
                logger.debug(f"过滤关系: {source_name} -[{rel_type}]-> {target_name}")
        
        logger.info(f"关系过滤: {len(relationships)} -> {len(filtered)}")
        return filtered


# 单例实例
_domain_filter_instance = None


def get_domain_filter() -> DomainFilter:
    """获取领域过滤器单例"""
    global _domain_filter_instance
    if _domain_filter_instance is None:
        _domain_filter_instance = DomainFilter()
    return _domain_filter_instance
