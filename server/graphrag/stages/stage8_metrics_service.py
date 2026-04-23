"""
阶段 8: 评价与反馈 (Metrics Service)

计算评价指标，收集反馈，形成治理闭环
"""

import logging
from typing import Dict, Any, List

from graphrag.config import get_config
from infra.neo4j_client import Neo4jClient

logger = logging.getLogger("graphrag.stage8")


class MetricsService:
    """
    评价指标服务
    
    计算量化指标，支持系统改进
    """
    
    def __init__(self):
        logger.info("MetricsService initialized")
        self.neo4j_client = Neo4jClient()
        self.neo4j_client.initialize()
        self.thresholds = get_config().thresholds

    @staticmethod
    def _safe_ratio(numerator: float, denominator: float) -> float:
        return float(numerator) / float(denominator) if denominator else 0.0
    
    def compute_metrics(self, doc_id: str) -> Dict[str, Any]:
        """
        计算文档的评价指标
        
        Args:
            doc_id: 文档 ID
        
        Returns:
            指标字典
        """
        logger.info("开始计算指标: doc_id=%s", doc_id)
        metrics: Dict[str, Any] = {
            "isolated_node_ratio": 0.0,
            "avg_degree": 0.0,
            "other_predicate_ratio": 0.0,
            "alias_count": 0,
            "modularity": 0.0
        }

        # 1) 获取该文档子图的所有节点（包括Document、Chunk、Concept、Claim、Entity等）
        # 使用Document作为入口点，找到所有相关节点
        nodes_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[*1..3]-(n)
        WHERE NOT (n:Document) OR n.id = $doc_id
        WITH COLLECT(DISTINCT d) + COLLECT(DISTINCT n) AS all_node_arrays
        UNWIND all_node_arrays AS node_array
        UNWIND node_array AS node
        RETURN count(DISTINCT node) AS total_nodes
        """
        nodes_result = self.neo4j_client.execute_query(nodes_query, {"doc_id": doc_id})
        total_nodes = nodes_result[0].get("total_nodes", 0) if nodes_result else 0

        # 2) 计算总边数（所有类型的边，包括CONTAINS、MENTIONS、EVIDENCE_FROM等）
        # 使用更简单的方式：找到所有相关节点ID，然后查询它们之间的边
        edges_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[*1..3]-(n)
        WHERE NOT (n:Document) OR n.id = $doc_id
        WITH COLLECT(DISTINCT d) + COLLECT(DISTINCT n) AS all_node_arrays
        UNWIND all_node_arrays AS node_array
        UNWIND node_array AS node
        WITH COLLECT(DISTINCT node) AS all_nodes
        UNWIND all_nodes AS source
        WITH source, all_nodes
        MATCH (source)-[r]->(target)
        WHERE target IN all_nodes
        RETURN count(DISTINCT r) AS edge_count
        """
        edges_result = self.neo4j_client.execute_query(edges_query, {"doc_id": doc_id})
        edge_count = edges_result[0].get("edge_count", 0) if edges_result else 0

        # 3) 计算平均度数（对于无向图：avg_degree = 2 * |E| / |V|）
        avg_degree = self._safe_ratio(2 * edge_count, total_nodes)

        # 4) 计算孤立节点比例（度数为0的节点）
        isolated_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[*1..3]-(n)
        WHERE NOT (n:Document) OR n.id = $doc_id
        WITH COLLECT(DISTINCT d) + COLLECT(DISTINCT n) AS all_node_arrays
        UNWIND all_node_arrays AS node_array
        UNWIND node_array AS node
        WITH COLLECT(DISTINCT node) AS all_nodes
        UNWIND all_nodes AS node
        OPTIONAL MATCH (node)-[r]-(other)
        WHERE other IN all_nodes
        WITH node, count(r) AS degree
        RETURN sum(CASE WHEN degree = 0 THEN 1 ELSE 0 END) AS isolated_nodes,
               count(node) AS total_nodes
        """
        isolated_result = self.neo4j_client.execute_query(isolated_query, {"doc_id": doc_id})
        isolated_nodes = isolated_result[0].get("isolated_nodes", 0) if isolated_result else 0
        total_for_iso = isolated_result[0].get("total_nodes", 0) if isolated_result else 0

        # 3) OTHER 谓词占比（仅统计该文档子图的关系）
        predicate_query = """
        MATCH (s)-[r:RELATION]->(t)
        WHERE s.doc_id = $doc_id AND t.doc_id = $doc_id
        RETURN count(r) AS total_rel,
               sum(CASE WHEN r.type = 'OTHER' THEN 1 ELSE 0 END) AS other_rel
        """
        pred_result = self.neo4j_client.execute_query(predicate_query, {"doc_id": doc_id})
        total_rel = pred_result[0].get("total_rel", 0) if pred_result else 0
        other_rel = pred_result[0].get("other_rel", 0) if pred_result else 0
        other_ratio = self._safe_ratio(other_rel, total_rel)

        # 4) Alias 数量（全局别名总数，当前未区分文档）
        alias_query = """
        MATCH (c:Concept)
        RETURN sum(size(coalesce(c.aliases, []))) AS alias_count
        """
        alias_result = self.neo4j_client.execute_query(alias_query)
        alias_count = alias_result[0].get("alias_count", 0) if alias_result else 0

        # 5) 社区模块度近似（同社区边比例，文档子图范围）
        modularity_query = """
        MATCH (n)-[r]-(m)
        WHERE n.doc_id = $doc_id AND m.doc_id = $doc_id AND elementId(n) < elementId(m)
              AND n.community_id IS NOT NULL AND m.community_id IS NOT NULL
        RETURN count(r) AS community_edges,
               sum(CASE WHEN n.community_id = m.community_id THEN 1 ELSE 0 END) AS intra_edges
        """
        mod_result = self.neo4j_client.execute_query(modularity_query, {"doc_id": doc_id})
        community_edges = mod_result[0].get("community_edges", 0) if mod_result else 0
        intra_edges = mod_result[0].get("intra_edges", 0) if mod_result else 0
        modularity = self._safe_ratio(intra_edges, community_edges)

        metrics.update(
            isolated_node_ratio=self._safe_ratio(isolated_nodes, total_for_iso),
            avg_degree=avg_degree,
            other_predicate_ratio=other_ratio,
            alias_count=alias_count,
            modularity=modularity,
        )
        
        logger.info("指标计算完成: %s", metrics)
        return metrics
    
    def check_alerts(self, metrics: Dict[str, Any]) -> List[str]:
        """
        检查告警
        
        Args:
            metrics: 指标字典
        
        Returns:
            告警列表
        """
        alerts = []
        iso_warn = self.thresholds.metrics.get("isolated_node_warning_ratio", 0.05)
        other_warn = self.thresholds.predicate_governance.get("other_predicate_warning_ratio", 0.1)
        if metrics.get("isolated_node_ratio", 0) > iso_warn:
            alerts.append(f"孤立节点比例过高: {metrics.get('isolated_node_ratio'):.3f} > {iso_warn}")
        if metrics.get("other_predicate_ratio", 0) > other_warn:
            alerts.append(f"OTHER 谓词占比过高: {metrics.get('other_predicate_ratio'):.3f} > {other_warn}")
        
        return alerts


__all__ = ["MetricsService"]

