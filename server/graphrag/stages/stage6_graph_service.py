"""
阶段 6: 幂等落库 (Graph Service)

将构建结果写入 Neo4j，确保幂等性与证据回溯
优化版本：仅存储5种允许的实体和5种允许的关系
"""

import logging
from typing import Dict, Any, List
from infra.neo4j_client import Neo4jClient
from graphrag.utils.domain_filter import get_domain_filter

logger = logging.getLogger("graphrag.stage6")

# 仅允许的5种实体类型
ALLOWED_ENTITY_TYPES = {
    "KnowledgePoint",  # 知识点
    "Content",         # 知识点内容
    "Document",        # 文档
    "Question",        # 题目
    "Timestamp"        # 时间戳
}

# 仅允许的5种关系类型
ALLOWED_RELATIONSHIP_TYPES = {
    "BELONGS_TO",      # 子知识点属于父知识点
    "FROM",            # 知识点从文档中提取
    "PRACTICES_IS",    # 题目中提到知识点
    "HAS_TIMESTAMP",   # 文档的更新时间戳
    "IS"               # 知识点的内容是什么
}


class GraphService:
    """
    图谱服务（软件工程领域优化版本）
    
    负责将构建结果写入 Neo4j，支持幂等性与证据回溯
    - 仅存储5种允许的实体类型
    - 仅存储5种允许的关系
    - 过滤所有其他实体和关系
    """
    
    def __init__(self):
        logger.info("GraphService initialized (software engineering domain, 5 entities & 5 relationships only)")
        self.neo4j_client = Neo4jClient()
        self.neo4j_client.initialize()
        self.domain_filter = get_domain_filter()
        
        # 统计信息
        self.stats = {
            "entities_written": 0,
            "entities_filtered": 0,
            "relationships_written": 0,
            "relationships_filtered": 0
        }
    
    def store_entity(self, entity_type: str, entity: Dict[str, Any]) -> bool:
        """
        存储实体节点（仅允许5种类型）
        
        Args:
            entity_type: 实体类型
            entity: 实体数据
        
        Returns:
            是否成功存储
        """
        # 1. 检查实体类型是否允许
        if entity_type not in ALLOWED_ENTITY_TYPES:
            logger.debug(f"过滤实体（类型不允许）: {entity_type} - {entity.get('name', entity.get('id'))}")
            self.stats["entities_filtered"] += 1
            return False
        
        # 2. 对KnowledgePoint进行额外的领域检查
        if entity_type == "KnowledgePoint":
            is_valid, domain_conf = self.domain_filter.is_software_engineering_entity(
                entity.get("name", ""),
                entity_type=entity_type
            )
            if not is_valid and domain_conf < 0.3:
                logger.debug(f"过滤知识点（不属于软件工程领域）: {entity.get('name')}")
                self.stats["entities_filtered"] += 1
                return False
        
        # 3. 根据实体类型调用相应的存储方法
        try:
            if entity_type == "KnowledgePoint":
                self._store_knowledge_point(entity)
            elif entity_type == "Content":
                self._store_content(entity)
            elif entity_type == "Document":
                self._store_document(entity)
            elif entity_type == "Question":
                self._store_question(entity)
            elif entity_type == "Timestamp":
                self._store_timestamp(entity)
            
            self.stats["entities_written"] += 1
            logger.debug(f"存储实体成功: {entity_type} - {entity.get('name', entity.get('id'))}")
            return True
        except Exception as e:
            logger.error(f"存储实体失败 ({entity_type}): {e}")
            return False
    
    def store_relationship(
        self,
        rel_type: str,
        source_id: str,
        target_id: str,
        rel_data: Dict[str, Any]
    ) -> bool:
        """
        存储关系（仅允许5种类型）
        
        Args:
            rel_type: 关系类型
            source_id: 源节点ID
            target_id: 目标节点ID
            rel_data: 关系数据
        
        Returns:
            是否成功存储
        """
        # 1. 检查关系类型是否允许
        if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
            logger.debug(f"过滤关系（类型不允许）: {source_id} -[{rel_type}]-> {target_id}")
            self.stats["relationships_filtered"] += 1
            return False
        
        # 2. 存储关系
        try:
            query = f"""
            MERGE (s {{id: $source_id}})
            MERGE (t {{id: $target_id}})
            MERGE (s)-[r:{rel_type}]->(t)
            SET r.confidence = $confidence,
                r.source_id = $source_id,
                r.target_id = $target_id,
                r.created_at = CASE WHEN r.created_at IS NULL THEN datetime() ELSE r.created_at END,
                r.updated_at = datetime()
            """
            
            params = {
                "source_id": source_id,
                "target_id": target_id,
                "confidence": rel_data.get("confidence", 0.8)
            }
            
            # 添加额外的关系属性
            for key, value in rel_data.items():
                if key != "confidence":
                    query += f",\n            r.{key} = ${key}"
                    params[key] = value
            
            self.neo4j_client.execute_query(query, params)
            self.stats["relationships_written"] += 1
            logger.debug(f"存储关系成功: {source_id} -[{rel_type}]-> {target_id}")
            return True
        except Exception as e:
            logger.error(f"存储关系失败: {e}")
            return False
    
    def _store_knowledge_point(self, kp: Dict[str, Any]):
        """存储知识点节点"""
        query = """
        MERGE (kp:KnowledgePoint {id: $id})
        SET kp.name = $name,
            kp.description = $description,
            kp.domain = $domain,
            kp.category = $category,
            kp.level = $level,
            kp.keywords = $keywords,
            kp.embedding = $embedding,
            kp.updated_at = datetime(),
            kp.created_at = CASE WHEN kp.created_at IS NULL THEN datetime() ELSE kp.created_at END
        """
        
        params = {
            "id": kp.get("id"),
            "name": kp.get("name"),
            "description": kp.get("description"),
            "domain": "software_engineering",
            "category": kp.get("category"),
            "level": kp.get("level"),
            "keywords": kp.get("keywords", []),
            "embedding": kp.get("embedding")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_content(self, content: Dict[str, Any]):
        """存储内容节点"""
        query = """
        MERGE (c:Content {id: $id})
        SET c.text = $text,
            c.type = $type,
            c.language = $language,
            c.code_snippet = $code_snippet,
            c.embedding = $embedding,
            c.updated_at = datetime(),
            c.created_at = CASE WHEN c.created_at IS NULL THEN datetime() ELSE c.created_at END
        """
        
        params = {
            "id": content.get("id"),
            "text": content.get("text"),
            "type": content.get("type"),
            "language": content.get("language"),
            "code_snippet": content.get("code_snippet"),
            "embedding": content.get("embedding")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_document(self, doc: Dict[str, Any]):
        """存储文档节点"""
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.url = $url,
            d.source_type = $source_type,
            d.author = $author,
            d.updated_at = datetime(),
            d.created_at = CASE WHEN d.created_at IS NULL THEN datetime() ELSE d.created_at END
        """
        
        params = {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "url": doc.get("url"),
            "source_type": doc.get("source_type"),
            "author": doc.get("author")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_question(self, q: Dict[str, Any]):
        """存储题目节点"""
        query = """
        MERGE (q:Question {id: $id})
        SET q.title = $title,
            q.description = $description,
            q.difficulty = $difficulty,
            q.category = $category,
            q.url = $url,
            q.updated_at = datetime(),
            q.created_at = CASE WHEN q.created_at IS NULL THEN datetime() ELSE q.created_at END
        """
        
        params = {
            "id": q.get("id"),
            "title": q.get("title"),
            "description": q.get("description"),
            "difficulty": q.get("difficulty"),
            "category": q.get("category"),
            "url": q.get("url")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_timestamp(self, ts: Dict[str, Any]):
        """存储时间戳节点"""
        query = """
        MERGE (t:Timestamp {id: $id})
        SET t.value = $value,
            t.formatted_date = $formatted_date,
            t.epoch_seconds = $epoch_seconds
        """
        
        params = {
            "id": ts.get("id"),
            "value": ts.get("value"),
            "formatted_date": ts.get("formatted_date"),
            "epoch_seconds": ts.get("epoch_seconds")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_chunk(self, chunk: Dict[str, Any]):
        """
        存储 Chunk 节点
        
        Args:
            chunk: Chunk 数据
        """
        logger.debug("存储 Chunk: %s", chunk.get("id"))
        
        query = """
        MERGE (c:Chunk {id: $id})
        SET c.doc_id = $doc_id,
            c.text = $text,
            c.resolved_text = $resolved_text,
            c.chunk_index = $chunk_index,
            c.section_path = $section_path,
            c.page_num = $page_num,
            c.sentence_ids = $sentence_ids,
            c.sentence_count = $sentence_count,
            c.window_start = $window_start,
            c.window_end = $window_end,
            c.embedding = $embedding,
            c.coreference_aliases = $coreference_aliases,
            c.coref_mode = $coref_mode,
            c.build_version = $build_version,
            c.updated_at = datetime(),
            c.created_at = CASE WHEN c.created_at IS NULL THEN datetime() ELSE c.created_at END
        """
        
        params = {
            "id": chunk.get("id"),
            "doc_id": chunk.get("doc_id"),
            "text": chunk.get("text"),
            "resolved_text": chunk.get("resolved_text"),
            "chunk_index": chunk.get("chunk_index"),
            "section_path": chunk.get("section_path"),
            "page_num": chunk.get("page_num"),
            "sentence_ids": chunk.get("sentence_ids", []),
            "sentence_count": chunk.get("sentence_count", 0),
            "window_start": chunk.get("window_start"),
            "window_end": chunk.get("window_end"),
            "embedding": chunk.get("embedding"),
            "coreference_aliases": chunk.get("coreference_aliases"),
            "coref_mode": chunk.get("coref_mode"),
            "build_version": chunk.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_concept(self, concept: Dict[str, Any]):
        """
        存储 Concept 节点
        
        Args:
            concept: Concept 数据
        """
        logger.debug("存储 Concept: %s", concept.get("id"))
        
        query = """
        MERGE (c:Concept {id: $id})
        SET c.name = $name,
            c.description = $description,
            c.domain = $domain,
            c.aliases = $aliases,
            c.importance = $importance,
            c.frequency = $frequency,
            c.embedding = $embedding,
            c.build_version = $build_version,
            c.updated_at = datetime(),
            c.created_at = CASE WHEN c.created_at IS NULL THEN datetime() ELSE c.created_at END
        """
        
        params = {
            "id": concept.get("id"),
            "name": concept.get("name"),
            "description": concept.get("description"),
            "domain": concept.get("domain"),
            "aliases": concept.get("aliases", []),
            "importance": concept.get("importance"),
            "frequency": concept.get("frequency"),
            "embedding": concept.get("embedding"),
            "build_version": concept.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_claim(self, claim: Dict[str, Any]):
        """
        存储 Claim 节点
        
        Args:
            claim: Claim 数据
        """
        logger.debug("存储 Claim: %s", claim.get("id"))
        
        query = """
        MERGE (cl:Claim {id: $id})
        SET cl.text = $text,
            cl.doc_id = $doc_id,
            cl.chunk_id = $chunk_id,
            cl.sentence_ids = $sentence_ids,
            cl.claim_type = $claim_type,
            cl.confidence = $confidence,
            cl.modality = $modality,
            cl.polarity = $polarity,
            cl.certainty = $certainty,
            cl.evidence_span = $evidence_span,
            cl.section_path = $section_path,
            cl.build_version = $build_version,
            cl.updated_at = datetime(),
            cl.created_at = CASE WHEN cl.created_at IS NULL THEN datetime() ELSE cl.created_at END
        """
        
        params = {
            "id": claim.get("id"),
            "text": claim.get("text"),
            "doc_id": claim.get("doc_id"),
            "chunk_id": claim.get("chunk_id"),
            "sentence_ids": claim.get("sentence_ids", []),
            "claim_type": claim.get("claim_type"),
            "confidence": claim.get("confidence"),
            "modality": claim.get("modality"),
            "polarity": claim.get("polarity"),
            "certainty": claim.get("certainty"),
            "evidence_span": claim.get("evidence_span"),
            "section_path": claim.get("section_path"),
            "build_version": claim.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_relation(self, relation: Dict[str, Any]):
        """
        存储关系
        
        Args:
            relation: 关系数据 {source_id, target_id, type, properties}
        """
        logger.debug("存储关系: %s -%s-> %s", relation.get("source_id"), relation.get("type"), relation.get("target_id"))
        
        query = """
        MATCH (s {id: $source_id}), (t {id: $target_id})
        MERGE (s)-[r:RELATION {id: $rel_id}]->(t)
        SET r.type = $type,
            r.weight = $weight,
            r.confidence = $confidence,
            r.properties = $properties,
            r.updated_at = datetime(),
            r.created_at = CASE WHEN r.created_at IS NULL THEN datetime() ELSE r.created_at END
        """
        
        import json
        # 生成关系 ID
        rel_id = f"{relation.get('source_id')}_{relation.get('type')}_{relation.get('target_id')}"
        
        # 将 properties 转换为 JSON 字符串
        properties_dict = relation.get("properties", {})
        properties_str = json.dumps(properties_dict) if properties_dict else "{}"
        
        params = {
            "source_id": relation.get("source_id"),
            "target_id": relation.get("target_id"),
            "rel_id": rel_id,
            "type": relation.get("type"),
            "weight": relation.get("weight", 1.0),
            "confidence": relation.get("confidence"),
            "properties": properties_str
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_with_provenance(
        self,
        node: Dict[str, Any],
        evidence_chunk_id: str,
        doc_id: str,
        section_path: str | None = None,
        sentence_ids: List[str] | None = None
    ):
        """
        存储节点并添加证据回溯
        
        Args:
            node: 节点数据
            evidence_chunk_id: 证据 Chunk ID
            doc_id: 文档 ID
            section_path: 章节路径
            sentence_ids: 句子 ID 列表
        """
        logger.debug("存储节点（带证据）: %s", node.get("id"))
        
        # 确定节点类型
        node_type = node.get("type", "Node")
        
        # 1. 存储节点（使用通用的属性集合）
        store_query = f"""
        MERGE (n:{node_type} {{id: $id}})
        SET n += $properties,
            n.updated_at = datetime(),
            n.created_at = CASE WHEN n.created_at IS NULL THEN datetime() ELSE n.created_at END
        RETURN n
        """
        
        params = {
            "id": node.get("id"),
            "properties": {k: v for k, v in node.items() if k != "id" and k != "type"}
        }
        
        self.neo4j_client.execute_query(store_query, params)
        
        # 2. 创建 EVIDENCE_FROM 关系（连接到证据 Chunk）
        evidence_query = """
        MATCH (n {id: $node_id}), (chunk:Chunk {id: $chunk_id})
        MERGE (n)-[e:EVIDENCE_FROM]->(chunk)
        SET e.doc_id = $doc_id,
            e.section_path = $section_path,
            e.sentence_ids = $sentence_ids,
            e.evidence_type = $evidence_type,
            e.timestamp = datetime(),
            e.created_at = CASE WHEN e.created_at IS NULL THEN datetime() ELSE e.created_at END
        """
        
        evidence_params = {
            "node_id": node.get("id"),
            "chunk_id": evidence_chunk_id,
            "doc_id": doc_id,
            "section_path": section_path,
            "sentence_ids": sentence_ids or [],
            "evidence_type": "EXTRACTED_FROM"
        }
        
        self.neo4j_client.execute_query(evidence_query, evidence_params)


__all__ = ["GraphService"]

