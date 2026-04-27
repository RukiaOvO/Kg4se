"""
阶段 5: 幂等落库 (Graph Service)

将构建结果写入 Neo4j，确保幂等性与证据回溯
使用 Neo4j 向量索引进行向量检索
"""

import logging
import json
from typing import Dict, Any, List
from infra.neo4j_client import Neo4jClient
from config import settings
from graphrag.utils.domain_filter import get_domain_filter

logger = logging.getLogger("graphrag.stage5")

ALLOWED_ENTITY_TYPES = {
    "Document",
    "Chunk",
    "Concept",
    "Claim",
    "Theme",
    "Entity",
}

ALLOWED_RELATIONSHIP_TYPES = {
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
}


class GraphService:
    """
    图谱服务
    
    负责将构建结果写入 Neo4j，支持幂等性与证据回溯
    """
    
    def __init__(self):
        logger.info("GraphService initialized")
        self.neo4j_client = Neo4jClient()
        self.neo4j_client.initialize()
        self.domain_filter = get_domain_filter()
        
        self.stats = {
            "entities_written": 0,
            "entities_filtered": 0,
            "relationships_written": 0,
            "relationships_filtered": 0
        }
    
    def store_entity(self, entity_type: str, entity: Dict[str, Any]) -> bool:
        """
        存储实体节点
        
        Args:
            entity_type: 实体类型
            entity: 实体数据
        
        Returns:
            是否成功存储
        """
        if entity_type not in ALLOWED_ENTITY_TYPES:
            logger.debug(f"过滤实体（类型不允许）: {entity_type} - {entity.get('name', entity.get('id'))}")
            self.stats["entities_filtered"] += 1
            return False
        
        try:
            if entity_type == "Document":
                self._store_document(entity)
            elif entity_type == "Chunk":
                self._store_chunk(entity)
            elif entity_type == "Concept":
                self._store_concept(entity)
            elif entity_type == "Claim":
                self._store_claim(entity)
            elif entity_type == "Theme":
                self._store_theme(entity)
            elif entity_type == "Entity":
                self._store_entity(entity)
            
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
        存储关系
        
        Args:
            rel_type: 关系类型
            source_id: 源节点ID
            target_id: 目标节点ID
            rel_data: 关系数据
        
        Returns:
            是否成功存储
        """
        if rel_type not in ALLOWED_RELATIONSHIP_TYPES:
            logger.debug(f"过滤关系（类型不允许）: {source_id} -[{rel_type}]-> {target_id}")
            self.stats["relationships_filtered"] += 1
            return False
        try:
            query = f"""
            OPTIONAL MATCH (s {{id: $source_id}})
            OPTIONAL MATCH (t {{id: $target_id}})
            WITH s, t
            WHERE s IS NOT NULL AND t IS NOT NULL
            MERGE (s)-[r:{rel_type}]->(t)
            SET r.confidence = $confidence,
                r.source_id = $source_id,
                r.target_id = $target_id,
                r.created_at = CASE WHEN r.created_at IS NULL THEN datetime() ELSE r.created_at END,
                r.updated_at = datetime()
            RETURN r
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
    
    def _store_document(self, doc: Dict[str, Any]):
        """存储文档节点"""
        query = """
        MERGE (d:Document {id: $id})
        SET d.title = $title,
            d.url = $url,
            d.source_type = $source_type,
            d.author = $author,
            d.doc_id = $doc_id,
            d.updated_at = datetime(),
            d.created_at = CASE WHEN d.created_at IS NULL THEN datetime() ELSE d.created_at END
        """
        
        params = {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "url": doc.get("url"),
            "source_type": doc.get("source_type"),
            "author": doc.get("author"),
            "doc_id": doc.get("doc_id")  # 存储 doc_id 属性
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_chunk(self, chunk: Dict[str, Any]):
        """存储 Chunk 节点（GraphRAG Pipeline）"""
        logger.debug(f"[Stage 6] 存储Chunk: id={chunk.get('id')}, doc_id={chunk.get('doc_id')}")
        
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
            # Neo4j 不支持 Map 类型，需要转换为 JSON 字符串
            "coreference_aliases": json.dumps(chunk.get("coreference_aliases")) if chunk.get("coreference_aliases") else None,
            "coref_mode": chunk.get("coref_mode"),
            "build_version": chunk.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_concept(self, concept: Dict[str, Any]):
        """存储 Concept 节点（GraphRAG Pipeline）"""
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
    
    def _store_claim(self, claim: Dict[str, Any]):
        """存储 Claim 节点（GraphRAG Pipeline）"""
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
    
    def _store_theme(self, theme: Dict[str, Any]):
        """存储 Theme 节点（GraphRAG Pipeline）"""
        query = """
        MERGE (t:Theme {id: $id})
        SET t.label = $label,
            t.summary = $summary,
            t.level = $level,
            t.member_count = $member_count,
            t.keywords = $keywords,
            t.embedding = $embedding,
            t.build_version = $build_version,
            t.updated_at = datetime(),
            t.created_at = CASE WHEN t.created_at IS NULL THEN datetime() ELSE t.created_at END
        """
        
        params = {
            "id": theme.get("id"),
            "label": theme.get("label"),
            "summary": theme.get("summary"),
            "level": theme.get("level"),
            "member_count": theme.get("member_count"),
            "keywords": theme.get("keywords", []),
            "embedding": theme.get("embedding"),
            "build_version": theme.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def _store_entity(self, entity: Dict[str, Any]):
        """存储 Entity 节点（GraphRAG Pipeline 通用实体）"""
        query = """
        MERGE (e:Entity {id: $id})
        SET e.name = $name,
            e.description = $description,
            e.type = $type,
            e.properties = $properties,
            e.embedding = $embedding,
            e.build_version = $build_version,
            e.updated_at = datetime(),
            e.created_at = CASE WHEN e.created_at IS NULL THEN datetime() ELSE e.created_at END
        """
        
        import json
        params = {
            "id": entity.get("id"),
            "name": entity.get("name"),
            "description": entity.get("description"),
            "type": entity.get("type"),
            "properties": json.dumps(entity.get("properties", {})),
            "embedding": entity.get("embedding"),
            "build_version": entity.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_chunk(self, chunk: Dict[str, Any]):
        """
        存储 Chunk 节点
        
        Args:
            chunk: Chunk 数据
        """
        chunk_id = chunk.get("id")
        doc_id = chunk.get("doc_id")
        logger.info(f"[Stage6] 存储 Chunk: id={chunk_id}, doc_id={doc_id}")
        
        # 关键修复：在创建Chunk节点前，先删除同ID的无标签节点
        # 这样可以避免之前 store_relationship 创建的无标签节点导致的问题
        cleanup_query = """
        MATCH (n)
        WHERE n.id = $id AND size(labels(n)) = 0
        DETACH DELETE n
        """
        self.neo4j_client.execute_query(cleanup_query, {"id": chunk_id})
        
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
            # Neo4j 不支持 Map 类型，需要转换为 JSON 字符串
            "coreference_aliases": json.dumps(chunk.get("coreference_aliases")) if chunk.get("coreference_aliases") else None,
            "coref_mode": chunk.get("coref_mode"),
            "build_version": chunk.get("build_version")
        }
        
        try:
            self.neo4j_client.execute_query(query, params)
            logger.info(f"[Stage6] Chunk 存储成功: id={chunk_id}, doc_id={doc_id}")
        except Exception as e:
            logger.error(f"[Stage6] Chunk 存储失败: id={chunk_id}, doc_id={doc_id}, error={e}", exc_info=True)
            raise
    
    def store_concept(self, concept: Dict[str, Any]):
        """
        存储 Concept 节点（支持增量构建：同名概念合并）
        
        Args:
            concept: Concept 数据
        """
        concept_id = concept.get("id")
        concept_name = concept.get("name")
        logger.debug(f"[Stage6] 存储 Concept: id={concept_id}, name={concept_name}")
        
        # 使用 ON CREATE SET / ON MATCH SET 处理已存在的概念
        # 同名概念会合并（MERGE on name），但保留原有的 id
        query = """
        MERGE (c:Concept {name: $name})
        ON CREATE SET
            c.id = $id,
            c.description = $description,
            c.domain = $domain,
            c.aliases = $aliases,
            c.importance = $importance,
            c.frequency = $frequency,
            c.embedding = $embedding,
            c.build_version = $build_version,
            c.created_at = datetime()
        ON MATCH SET
            c.description = CASE WHEN $description IS NOT NULL THEN $description ELSE c.description END,
            c.domain = CASE WHEN $domain IS NOT NULL THEN $domain ELSE c.domain END,
            c.importance = CASE WHEN $importance IS NOT NULL AND $importance > c.importance THEN $importance ELSE c.importance END,
            c.embedding = CASE WHEN $embedding IS NOT NULL THEN $embedding ELSE c.embedding END,
            c.frequency = coalesce(c.frequency, 0) + 1,
            c.updated_at = datetime()
        """
        
        params = {
            "id": concept.get("id"),
            "name": concept.get("name"),
            "description": concept.get("description"),
            "domain": concept.get("domain"),
            "aliases": concept.get("aliases", []),
            "importance": concept.get("importance"),
            "frequency": 1,
            "embedding": concept.get("embedding"),
            "build_version": concept.get("build_version")
        }
        
        try:
            self.neo4j_client.execute_query(query, params)
            logger.debug(f"[Stage6] Concept 存储成功: name={concept_name}")
        except Exception as e:
            logger.error(f"[Stage6] Concept 存储失败: name={concept_name}, error={e}", exc_info=True)
            raise
    
    def store_claim(self, claim: Dict[str, Any]):
        """
        存储 Claim 节点
        Args:
            claim: Claim 数据
        """
        claim_id = claim.get("id")
        logger.debug(f"[Stage6] 存储 Claim: {claim_id}")
        
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
            cl.embedding = $embedding,
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
            "embedding": claim.get("embedding"),
            "build_version": claim.get("build_version")
        }
        
        self.neo4j_client.execute_query(query, params)
    
    def store_relation(self, relation: Dict[str, Any]):
        """
        存储关系
        
        Args:
            relation: 关系数据 {source_id, target_id, type, properties}
        """
        source_id = relation.get("source_id")
        target_id = relation.get("target_id")
        rel_type = relation.get("type")
        logger.debug(f"[Stage6] 存储关系: {source_id} -[{rel_type}]-> {target_id}")
        
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

