"""Graph service for ingesting triplets into Neo4j."""
from typing import List, Dict, Any, Optional
from models.document import Triplet
from config.instances import get_instance, InstanceNames
from utils.logger import get_logger

logger = get_logger("services.graph_service")


class GraphService:
    """Service for graph operations."""
    
    @property
    def neo4j_client(self):
        """Get Neo4j client from instance registry."""
        return get_instance(InstanceNames.NEO4J_CLIENT)
    
    def ingest_triplets(self, doc_id: str, triplets: List[Triplet], root_topic: Optional[str] = None):
        """
        Ingest triplets into Neo4j graph.
        
        Args:
            doc_id: Document ID
            triplets: List of triplets to ingest
            root_topic: Optional root topic name. If provided, concepts will be linked to topic instead of document.
        """
        logger.info(f"[Graph Service] Starting to ingest {len(triplets)} triplets into Neo4j...")
        if root_topic:
            logger.info(f"   Root topic: {root_topic}")
        
        if root_topic:
            self.neo4j_client.create_or_get_topic(root_topic)
            self.neo4j_client.link_document_to_topic(doc_id, root_topic)
        
        created_concepts = set()
        created_relationships = 0
        
        for idx, triplet in enumerate(triplets, 1):
            if triplet.subject not in created_concepts:
                self.neo4j_client.create_concept(triplet.subject)
                created_concepts.add(triplet.subject)
            
            if triplet.object not in created_concepts:
                self.neo4j_client.create_concept(triplet.object)
                created_concepts.add(triplet.object)
            
            rel_type = triplet.predicate.upper().replace(" ", "_")
            self.neo4j_client.create_relationship(
                source_id=triplet.subject,
                target_id=triplet.object,
                rel_type=rel_type,
                properties={
                    "confidence": triplet.confidence,
                    "evidence": triplet.evidence,
                    "doc_id": doc_id,
                    "chunk_id": triplet.chunk_id
                }
            )
            created_relationships += 1
            
            if idx <= 5:
                logger.debug(f"   [{idx}] {triplet.subject} --[{rel_type}]--> {triplet.object} (confidence: {triplet.confidence:.2f})")
            
            if root_topic:
                self.neo4j_client.link_concept_to_topic(
                    concept_name=triplet.subject,
                    topic_name=root_topic,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500],
                    doc_id=doc_id
                )
                
                self.neo4j_client.link_concept_to_topic(
                    concept_name=triplet.object,
                    topic_name=root_topic,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500],
                    doc_id=doc_id
                )
            elif doc_id:
                self.neo4j_client.link_concept_to_document(
                    concept_name=triplet.subject,
                    doc_id=doc_id,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500]
                )
                
                self.neo4j_client.link_concept_to_document(
                    concept_name=triplet.object,
                    doc_id=doc_id,
                    page=triplet.evidence.get("page"),
                    offset=triplet.evidence.get("offset"),
                    evidence=triplet.evidence.get("text", "")[:500]
                )
        
        if len(triplets) > 5:
            logger.debug(f"   ... 还有 {len(triplets) - 5} 个三元组")
        
        logger.info(f"✅ [图谱构建] 完成:")
        logger.info(f"   - 创建/更新概念数: {len(created_concepts)}")
        logger.info(f"   - 创建关系数: {created_relationships}")
    
    def ingest_rich_concepts(self, doc_id: str, concepts: List[Dict[str, Any]], root_topic: Optional[str] = None):
        """
        将AI提取的丰富概念信息写入Neo4j。
        
        Args:
            doc_id: 文档ID
            concepts: 概念列表，包含详细属性
            root_topic: Optional root topic name. If provided, concepts will be linked to topic instead of document.
        """
        logger.info(f"💎 [丰富概念] 开始写入 {len(concepts)} 个增强概念...")
        if root_topic:
            logger.info(f"   📌 主题根节点: {root_topic}")
        
        if root_topic:
            self.neo4j_client.create_or_get_topic(root_topic)
            self.neo4j_client.link_document_to_topic(doc_id, root_topic)
        
        for idx, concept in enumerate(concepts, 1):
            name = concept.get("name", "")
            if not name:
                continue
            
            properties = {
                "description": concept.get("description", ""),
                "domain": concept.get("domain", ""),
                "category": concept.get("category", ""),
                "importance": concept.get("importance", "medium")
            }
            
            if concept.get("attributes"):
                properties.update(concept["attributes"])
            
            self.neo4j_client.execute_query(
                """
                MERGE (c:Concept {name: $name})
                SET c += $properties
                SET c.updated_at = datetime()
                """,
                {
                    "name": name,
                    "properties": properties
                }
            )
            
            aliases = concept.get("aliases", [])
            if aliases:
                for alias in aliases:
                    self.neo4j_client.execute_query(
                        """
                        MATCH (c:Concept {name: $name})
                        MERGE (a:Alias {name: $alias})
                        MERGE (a)-[:ALIAS_OF]->(c)
                        """,
                        {"name": name, "alias": alias}
                    )
            
            if root_topic:
                self.neo4j_client.link_concept_to_topic(
                    concept_name=name,
                    topic_name=root_topic,
                    doc_id=doc_id
                )
            elif doc_id:
                self.neo4j_client.link_concept_to_document(
                    concept_name=name,
                    doc_id=doc_id
                )
            
            if idx <= 3:
                logger.debug(f"   [{idx}] {name} ({concept.get('category', 'unknown')}) - {concept.get('description', '')[:50]}...")
        
        if len(concepts) > 3:
            logger.debug(f"   ... 还有 {len(concepts) - 3} 个概念")
        
        logger.info(f"✅ [丰富概念] 完成")


    def ingest_chunks(self, doc_id: str, chunks: List[Any]) -> int:
        """
        保存文本块到 Neo4j。

        Args:
            doc_id: 文档ID
            chunks: Chunk 对象列表

        Returns:
            保存的文本块数量
        """
        logger.info(f"📄 [文本块存储] 开始保存 {len(chunks)} 个文本块...")

        saved_count = 0
        for i, chunk in enumerate(chunks, 1):
            try:
                chunk_id = f"{doc_id}_{chunk.chunk_id}"

                import json
                meta_json = json.dumps(chunk.meta) if chunk.meta else None

                self.neo4j_client.execute_query("""
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.doc_id = $doc_id,
                        c.text = $text,
                        c.meta = $meta_json,
                        c.created_at = datetime(),
                        c.updated_at = datetime()
                    RETURN c
                """, {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "text": chunk.text,
                    "meta_json": meta_json
                })

                self.neo4j_client.execute_query("""
                    MATCH (d:Document {id: $doc_id})
                    MATCH (c:Chunk {id: $chunk_id})
                    MERGE (d)-[:HAS_CHUNK]->(c)
                """, {
                    "doc_id": doc_id,
                    "chunk_id": chunk_id
                })

                saved_count += 1

                if i <= 3:
                    logger.debug(f"   [{i}] 已保存: {chunk_id} ({len(chunk.text)} 字符)")

            except Exception as e:
                logger.warning(f"⚠️  保存文本块失败: {chunk.chunk_id}, 错误: {str(e)}")

        logger.info(f"✅ [文本块存储] 完成: {saved_count}/{len(chunks)} 个文本块")
        return saved_count