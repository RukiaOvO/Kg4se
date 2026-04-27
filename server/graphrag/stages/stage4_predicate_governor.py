"""
阶段 4: 谓词治理 (Predicate Governor)

规范化谓词，映射自然语言关系到标准谓词集
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from graphrag.config import get_config, ConstraintResult, GovernanceStatus

logger = logging.getLogger("graphrag.stage4")

ALLOWED_PREDICATES = {
    "MENTIONS",
    "CONTAINS_CLAIM",
    "BELONGS_TO_THEME",
    "RELATED_TO",
    "SUPPORTS",
    "CONTRADICTS",
    "EVIDENCE_FROM",
    "CONTAINS",
    "BELONGS_TO",
    "RELATION",
    "USES",
    "IMPLEMENTS",
    "COMPARES_WITH",
    "DEPENDS_ON",
}


class PredicateGovernor:
    """
    谓词治理器
    
    将自然语言谓词映射到标准谓词集，并验证类型约束
    """
    
    def __init__(self):
        self.config = get_config()
        logger.info("PredicateGovernor initialized")
    
    def normalize(self, predicate: str, source_type: str, target_type: str) -> Dict[str, Any]:
        """
        规范化谓词并返回治理结果
        
        Args:
            predicate: 原始谓词
            source_type: 源节点类型
            target_type: 目标节点类型
        
        Returns:
            包含治理结果的字典
        """
        logger.debug(f"规范化谓词: {predicate} ({source_type} -> {target_type})")
        
        result = {
            'original_predicate': predicate,
            'normalized_predicate': None,
            'confidence': 0.0,
            'constraint_result': ConstraintResult.HARD_VIOLATION,
            'governance_status': GovernanceStatus.REJECTED,
            'predicate_version': self.config.predicates.version,
            'ontology_version': self.config.ontology.version,
            'reason': '谓词不在允许列表中'
        }
        
        if predicate in ALLOWED_PREDICATES:
            is_valid = self._validate_type_constraint(
                source_type, predicate, target_type
            )
            
            if is_valid:
                result.update({
                    'normalized_predicate': predicate,
                    'confidence': 1.0,
                    'constraint_result': ConstraintResult.PASS,
                    'governance_status': GovernanceStatus.ACCEPTED,
                    'reason': '标准谓词，类型约束通过'
                })
                logger.debug(f"✅ 标准谓词通过验证: {predicate}")
                return result
            else:
                result.update({
                    'constraint_result': ConstraintResult.HARD_VIOLATION,
                    'governance_status': GovernanceStatus.REJECTED,
                    'reason': f'类型约束失败: {source_type} -{predicate}-> {target_type}'
                })
                logger.warning(f"❌ 标准谓词类型约束失败: {source_type} -{predicate}-> {target_type}")
                return result
        
        normalized = self._map_to_allowed_predicate(predicate)
        if normalized:
            is_valid = self._validate_type_constraint(
                source_type, normalized, target_type
            )
            
            if is_valid:
                result.update({
                    'normalized_predicate': normalized,
                    'confidence': 0.9,
                    'constraint_result': ConstraintResult.PASS,
                    'governance_status': GovernanceStatus.ACCEPTED,
                    'reason': f'自然语言谓词映射: {predicate} -> {normalized}'
                })
                logger.debug(f"✅ 谓词映射成功: {predicate} -> {normalized}")
                return result
            else:
                result.update({
                    'constraint_result': ConstraintResult.HARD_VIOLATION,
                    'governance_status': GovernanceStatus.REJECTED,
                    'reason': f'映射后类型约束失败: {source_type} -{normalized}-> {target_type}'
                })
                logger.warning(f"❌ 映射谓词类型约束失败: {source_type} -{normalized}-> {target_type}")
                return result
        
        result.update({
            'confidence': 0.0,
            'governance_status': GovernanceStatus.REJECTED,
            'reason': f'谓词 "{predicate}" 无法映射到允许列表中的标准谓词'
        })
        logger.warning(f"❌ 谓词被拒绝（不在允许列表中）: {predicate}")
        return result
    
    def _map_to_allowed_predicate(self, predicate: str) -> Optional[str]:
        """
        尝试将自然语言谓词映射到允许的谓词之一
        
        Args:
            predicate: 原始谓词
        
        Returns:
            映射后的标准谓词，或 None
        """
        predicate_lower = predicate.lower().strip()
        
        mappings = {
            "属于": "BELONGS_TO",
            "隶属于": "BELONGS_TO",
            "is_a": "BELONGS_TO",
            "subclass_of": "BELONGS_TO",
            "子类": "BELONGS_TO",
            "分类": "BELONGS_TO",
            "归类": "BELONGS_TO",
            
            "来自": "EVIDENCE_FROM",
            "源自": "EVIDENCE_FROM",
            "来源于": "EVIDENCE_FROM",
            "提取自": "EVIDENCE_FROM",
            "extracted_from": "EVIDENCE_FROM",
            "出自": "EVIDENCE_FROM",
            
            "提到": "MENTIONS",
            "提及": "MENTIONS",
            "引用": "MENTIONS",
            "mentions": "MENTIONS",
            "references": "MENTIONS",
            "引用了": "MENTIONS",
            "在...中提到": "MENTIONS",
            
            "包含": "CONTAINS",
            "包含了": "CONTAINS",
            "contains": "CONTAINS",
            
            "相关": "RELATED_TO",
            "与...相关": "RELATED_TO",
            "关联": "RELATED_TO",
            "relates_to": "RELATED_TO",
            "related_to": "RELATED_TO",
            "联系": "RELATED_TO",
            
            "使用": "USES",
            "采用": "USES",
            "uses": "USES",
            "utilizes": "USES",
            
            "实现": "IMPLEMENTS",
            "实现了": "IMPLEMENTS",
            "implements": "IMPLEMENTS",
            
            "比较": "COMPARES_WITH",
            "对比": "COMPARES_WITH",
            "compared_with": "COMPARES_WITH",
            
            "依赖": "DEPENDS_ON",
            "依赖于": "DEPENDS_ON",
            "depends_on": "DEPENDS_ON",
            
            "支持": "SUPPORTS",
            "supports": "SUPPORTS",
            
            "反驳": "CONTRADICTS",
            "contradicts": "CONTRADICTS",
            "与...矛盾": "CONTRADICTS",
        }
        
        if predicate_lower in mappings:
            return mappings[predicate_lower]
        
        for key, value in mappings.items():
            if key in predicate_lower or predicate_lower in key:
                return value
        
        return None
    
    def _validate_type_constraint(self, source_type: str, predicate: str, target_type: str) -> bool:
        """
        验证类型约束
        
        Args:
            source_type: 源节点类型
            predicate: 谓词
            target_type: 目标节点类型
        
        Returns:
            是否通过约束验证
        """
        type_constraints = {
            "MENTIONS": {
                "sources": ["Chunk", "Document"],
                "targets": ["Concept", "Claim"]
            },
            "CONTAINS_CLAIM": {
                "sources": ["Chunk"],
                "targets": ["Claim"]
            },
            "BELONGS_TO_THEME": {
                "sources": ["Concept"],
                "targets": ["Theme"]
            },
            "RELATED_TO": {
                "sources": ["Concept", "Claim", "Document"],
                "targets": ["Concept", "Claim", "Document"]
            },
            "SUPPORTS": {
                "sources": ["Claim"],
                "targets": ["Concept", "Claim"]
            },
            "CONTRADICTS": {
                "sources": ["Claim"],
                "targets": ["Concept", "Claim"]
            },
            "EVIDENCE_FROM": {
                "sources": ["Concept", "Claim"],
                "targets": ["Chunk"]
            },
            "CONTAINS": {
                "sources": ["Document"],
                "targets": ["Chunk"]
            },
            "BELONGS_TO": {
                "sources": ["Concept", "Document"],
                "targets": ["Concept", "Document", "Theme"]
            },
            "RELATION": {
                "sources": ["Concept", "Claim", "Document", "Chunk"],
                "targets": ["Concept", "Claim", "Document", "Chunk"]
            },
            "USES": {
                "sources": ["Concept"],
                "targets": ["Concept"]
            },
            "IMPLEMENTS": {
                "sources": ["Concept"],
                "targets": ["Concept"]
            },
            "COMPARES_WITH": {
                "sources": ["Concept"],
                "targets": ["Concept"]
            },
            "DEPENDS_ON": {
                "sources": ["Concept"],
                "targets": ["Concept"]
            },
        }
        
        if predicate not in type_constraints:
            logger.warning(f"未知谓词: {predicate}")
            return False
        
        constraint = type_constraints[predicate]
        
        if source_type not in constraint["sources"]:
            logger.warning(
                f"源节点类型不匹配 ({predicate}): "
                f"期望 {constraint['sources']}，得到 {source_type}"
            )
            return False
        
        if target_type not in constraint["targets"]:
            logger.warning(
                f"目标节点类型不匹配 ({predicate}): "
                f"期望 {constraint['targets']}，得到 {target_type}"
            )
            return False
        
        return True
    
    def normalize_all(self, doc_id: str):
        """
        批量规范化文档的所有关系谓词，并写入治理元数据
        
        Args:
            doc_id: 文档 ID
        """
        logger.info(f"开始批量规范化: doc_id={doc_id}")
        
        from infra.neo4j_client import neo4j_client
        
        query = """
        MATCH (d:Document {id: $doc_id})-[*1..3]-(n1)-[r]->(n2)
        WHERE type(r) <> 'CONTAINS' AND type(r) <> 'MENTIONS' 
              AND type(r) <> 'CONTAINS_CLAIM' AND type(r) <> 'EVIDENCE_FROM'
              AND (r.governance_status IS NULL OR r.governance_version <> $predicate_version)
        RETURN DISTINCT type(r) AS rel_type, 
               labels(n1)[0] AS source_type,
               labels(n2)[0] AS target_type,
               elementId(r) AS rel_id,
               properties(r) AS props
        """
        
        result = neo4j_client.execute_query(query, {
            "doc_id": doc_id, 
            "predicate_version": self.config.predicates.version
        })
        
        logger.debug(f"[Stage5] 查询返回: {len(result)} 条待处理关系")
        
        stats = {
            'accepted': 0,
            'pending': 0,
            'rejected': 0,
            'soft_violations': 0
        }
        
        unique_predicates = set()
        
        for record in result:
            rel_type = record.get("rel_type")
            source_type = record.get("source_type", "Concept")
            target_type = record.get("target_type", "Concept")
            rel_id = record.get("rel_id")
            props = record.get("props", {})
            
            unique_predicates.add(rel_type)
            
            governance_result = self.normalize(rel_type, source_type, target_type)
            
            status = governance_result['governance_status']
            if status == GovernanceStatus.ACCEPTED:
                stats['accepted'] += 1
            elif status == GovernanceStatus.PENDING:
                stats['pending'] += 1
            else:
                stats['rejected'] += 1
                
            if governance_result['constraint_result'] == ConstraintResult.SOFT_VIOLATION:
                stats['soft_violations'] += 1
        
        logger.debug(f"[Stage5] 唯一谓词类型: {unique_predicates}")
        
        for record in result:
            rel_type = record.get("rel_type")
            source_type = record.get("source_type", "Concept")
            target_type = record.get("target_type", "Concept")
            rel_id = record.get("rel_id")
            props = record.get("props", {})
            
            governance_result = self.normalize(rel_type, source_type, target_type)
            
            governance_metadata = {
                'original_predicate': governance_result['original_predicate'],
                'confidence': governance_result['confidence'],
                'constraint_result': governance_result['constraint_result'].value,
                'governance_status': governance_result['governance_status'].value,
                'predicate_version': governance_result['predicate_version'],
                'ontology_version': governance_result['ontology_version'],
                'governed_at': datetime.utcnow().isoformat()
            }
            
            if governance_result['normalized_predicate'] != rel_type:
                normalized_rel_type = governance_result['normalized_predicate'].replace('(', '_').replace(')', '')
                
                update_query = f"""
                MATCH ()-[r]->()
                WHERE elementId(r) = $rel_id
                WITH r, startNode(r) AS source, endNode(r) AS target, properties(r) AS props
                DELETE r
                CREATE (source)-[r2:{normalized_rel_type}]->(target)
                SET r2 = props, r2 += $metadata
                """
            else:
                update_query = """
                MATCH ()-[r]->()
                WHERE elementId(r) = $rel_id
                SET r += $metadata
                """
            
            try:
                neo4j_client.execute_query(update_query, {
                    "rel_id": rel_id,
                    "metadata": governance_metadata
                })
                
                if governance_result['governance_status'] == GovernanceStatus.ACCEPTED:
                    logger.debug(f"关系已接受: {rel_type} -> {governance_result['normalized_predicate']}")
                elif governance_result['governance_status'] == GovernanceStatus.PENDING:
                    logger.warning(f"关系待复核: {rel_type} -> {governance_result['normalized_predicate']}")
                else:
                    logger.error(f"关系被拒绝: {rel_type} -> {governance_result['normalized_predicate']}")
                    
            except Exception as e:
                logger.error(f"更新关系失败: {e}")
        
        logger.info(f"批量规范化完成: doc_id={doc_id}, accepted={stats['accepted']}, "
                   f"pending={stats['pending']}, rejected={stats['rejected']}, "
                   f"soft_violations={stats['soft_violations']}")
        
        return stats
    
    def get_governance_stats(self, doc_id: str = None) -> Dict[str, Any]:
        """获取治理统计信息"""
        from server.infra.neo4j_client import neo4j_client
        
        if doc_id:
            query = """
            MATCH (d:Document {id: $doc_id})-[*1..3]-(n1)-[r]->(n2)
            WHERE r.governance_status IS NOT NULL
            RETURN r.governance_status AS status,
                   r.constraint_result AS constraint,
                   COUNT(*) AS count
            """
            params = {"doc_id": doc_id}
        else:
            query = """
            MATCH ()-[r]->()
            WHERE r.governance_status IS NOT NULL
            RETURN r.governance_status AS status,
                   r.constraint_result AS constraint,
                   COUNT(*) AS count
            """
            params = {}
        
        result = neo4j_client.execute_query(query, params)
        
        stats = {
            'total': 0,
            'accepted': 0,
            'pending': 0,
            'rejected': 0,
            'soft_violations': 0,
            'hard_violations': 0,
            'by_status': {},
            'by_constraint': {}
        }
        
        for record in result:
            status = record.get("status", "unknown")
            constraint = record.get("constraint", "unknown")
            count = record.get("count", 0)
            
            stats['total'] += count
            
            if status not in stats['by_status']:
                stats['by_status'][status] = 0
            stats['by_status'][status] += count
            
            if constraint not in stats['by_constraint']:
                stats['by_constraint'][constraint] = 0
            stats['by_constraint'][constraint] += count
            
            if status == 'accepted':
                stats['accepted'] += count
            elif status == 'pending':
                stats['pending'] += count
            elif status == 'rejected':
                stats['rejected'] += count
                
            if constraint == 'soft':
                stats['soft_violations'] += count
            elif constraint == 'hard':
                stats['hard_violations'] += count
        
        return stats
    
    def get_pending_relations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取待复核的关系列表"""
        from infra.neo4j_client import neo4j_client
        
        query = """
        MATCH ()-[r]->()
        WHERE r.governance_status = 'pending'
        RETURN r.original_predicate AS original,
               r.normalized_predicate AS normalized,
               r.confidence AS confidence,
               r.constraint_result AS constraint,
               startNode(r).name AS source_name,
               labels(startNode(r))[0] AS source_type,
               endNode(r).name AS target_name,
               labels(endNode(r))[0] AS target_type
        LIMIT $limit
        """
        
        result = neo4j_client.execute_query(query, {"limit": limit})
        
        return [dict(record) for record in result]


__all__ = ["PredicateGovernor"]
