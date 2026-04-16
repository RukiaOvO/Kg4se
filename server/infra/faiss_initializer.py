"""FAISS index initializer - import vectors from Neo4j."""

import logging
from typing import List, Dict, Any

from infra.neo4j_client import neo4j_client
from infra.faiss_store import faiss_store
from infra.config import settings

logger = logging.getLogger("infra.faiss_initializer")


class FaissInitializer:
    """Initialize FAISS index from Neo4j data."""
    
    def __init__(self):
        self.neo4j = neo4j_client
        self.faiss = faiss_store
    
    def import_concept_vectors(self) -> int:
        """
        Import concept vectors from Neo4j to FAISS.
        
        Returns:
            Number of vectors imported
        """
        logger.info("Starting concept vector import from Neo4j")
        
        query = """
        MATCH (c:Concept)
        WHERE c.embedding IS NOT NULL
        RETURN c.name AS id, c.embedding AS embedding, 
               c.domain AS domain, c.aliases AS aliases
        """
        
        try:
            results = self.neo4j.execute_query(query)
            
            if not results:
                logger.info("No concept vectors found in Neo4j")
                return 0
            
            ids = []
            embeddings = []
            metadata_list = []
            
            for record in results:
                concept_id = record.get("id", "")
                embedding = record.get("embedding", [])
                
                if not concept_id or not embedding:
                    continue
                
                ids.append(concept_id)
                embeddings.append(embedding)
                metadata_list.append({
                    "type": "concept",
                    "domain": record.get("domain"),
                    "aliases": record.get("aliases", [])
                })
            
            if embeddings:
                success = self.faiss.insert(embeddings, ids, metadata_list)
                if success:
                    logger.info(f"Successfully imported {len(embeddings)} concept vectors")
                    return len(embeddings)
                else:
                    logger.error("Failed to insert concept vectors into FAISS")
                    return 0
            
            return 0
        
        except Exception as e:
            logger.error(f"Failed to import concept vectors: {e}")
            return 0
    
    def import_claim_vectors(self) -> int:
        """
        Import claim vectors from Neo4j to FAISS.
        
        Returns:
            Number of vectors imported
        """
        logger.info("Starting claim vector import from Neo4j")
        
        query = """
        MATCH (cl:Claim)
        WHERE cl.embedding IS NOT NULL
        RETURN cl.id AS id, cl.embedding AS embedding,
               cl.text AS text, cl.confidence AS confidence,
               cl.claim_type AS claim_type, cl.doc_id AS doc_id,
               cl.chunk_id AS chunk_id
        """
        
        try:
            results = self.neo4j.execute_query(query)
            
            if not results:
                logger.info("No claim vectors found in Neo4j")
                return 0
            
            ids = []
            embeddings = []
            metadata_list = []
            
            for record in results:
                claim_id = record.get("id", "")
                embedding = record.get("embedding", [])
                
                if not claim_id or not embedding:
                    continue
                
                ids.append(claim_id)
                embeddings.append(embedding)
                metadata_list.append({
                    "type": "claim",
                    "text": record.get("text"),
                    "confidence": record.get("confidence"),
                    "claim_type": record.get("claim_type"),
                    "doc_id": record.get("doc_id"),
                    "chunk_id": record.get("chunk_id")
                })
            
            if embeddings:
                success = self.faiss.insert(embeddings, ids, metadata_list)
                if success:
                    logger.info(f"Successfully imported {len(embeddings)} claim vectors")
                    return len(embeddings)
                else:
                    logger.error("Failed to insert claim vectors into FAISS")
                    return 0
            
            return 0
        
        except Exception as e:
            logger.error(f"Failed to import claim vectors: {e}")
            return 0
    
    def import_document_vectors(self) -> int:
        """
        Import document vectors from Neo4j to FAISS.
        
        Returns:
            Number of vectors imported
        """
        logger.info("Starting document vector import from Neo4j")
        
        query = """
        MATCH (d:Document)
        WHERE d.embedding IS NOT NULL
        RETURN d.id AS id, d.embedding AS embedding,
               d.filename AS filename, d.kind AS kind,
               d.checksum AS checksum
        """
        
        try:
            results = self.neo4j.execute_query(query)
            
            if not results:
                logger.info("No document vectors found in Neo4j")
                return 0
            
            ids = []
            embeddings = []
            metadata_list = []
            
            for record in results:
                doc_id = record.get("id", "")
                embedding = record.get("embedding", [])
                
                if not doc_id or not embedding:
                    continue
                
                ids.append(doc_id)
                embeddings.append(embedding)
                metadata_list.append({
                    "type": "document",
                    "filename": record.get("filename"),
                    "kind": record.get("kind"),
                    "checksum": record.get("checksum")
                })
            
            if embeddings:
                success = self.faiss.insert(embeddings, ids, metadata_list)
                if success:
                    logger.info(f"Successfully imported {len(embeddings)} document vectors")
                    return len(embeddings)
                else:
                    logger.error("Failed to insert document vectors into FAISS")
                    return 0
            
            return 0
        
        except Exception as e:
            logger.error(f"Failed to import document vectors: {e}")
            return 0
    
    def import_all_vectors(self) -> Dict[str, int]:
        """
        Import all vectors from Neo4j to FAISS.
        
        Returns:
            Dictionary with counts for each type
        """
        logger.info("Starting full vector import from Neo4j")
        
        try:
            self.neo4j.initialize()
            
            counts = {
                "concepts": self.import_concept_vectors(),
                "claims": self.import_claim_vectors(),
                "documents": self.import_document_vectors()
            }
            
            total = sum(counts.values())
            logger.info(f"Full import completed: {total} vectors imported")
            
            # Save the index
            if total > 0:
                self.faiss.save_index(settings.faiss_index_path)
            
            return counts
        
        except Exception as e:
            logger.error(f"Failed to import vectors: {e}")
            return {"concepts": 0, "claims": 0, "documents": 0}
    
    def sync_vectors(self) -> Dict[str, int]:
        """
        Synchronize vectors between Neo4j and FAISS.
        
        This will:
        1. Clear existing FAISS index
        2. Import all vectors from Neo4j
        
        Returns:
            Dictionary with counts for each type
        """
        logger.info("Starting vector synchronization")
        
        try:
            # Clear existing index
            self.faiss.clear()
            logger.info("Cleared existing FAISS index")
            
            # Import all vectors
            return self.import_all_vectors()
        
        except Exception as e:
            logger.error(f"Failed to sync vectors: {e}")
            return {"concepts": 0, "claims": 0, "documents": 0}
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get synchronization status."""
        try:
            faiss_stats = self.faiss.get_stats()
            
            # Get counts from Neo4j
            concept_count = self.neo4j.execute_query(
                "MATCH (c:Concept) WHERE c.embedding IS NOT NULL RETURN count(c) as count"
            )
            claim_count = self.neo4j.execute_query(
                "MATCH (cl:Claim) WHERE cl.embedding IS NOT NULL RETURN count(cl) as count"
            )
            doc_count = self.neo4j.execute_query(
                "MATCH (d:Document) WHERE d.embedding IS NOT NULL RETURN count(d) as count"
            )
            
            return {
                "faiss_vector_count": faiss_stats.get("vector_count", 0),
                "neo4j_concept_count": concept_count[0]["count"] if concept_count else 0,
                "neo4j_claim_count": claim_count[0]["count"] if claim_count else 0,
                "neo4j_document_count": doc_count[0]["count"] if doc_count else 0,
                "index_type": faiss_stats.get("index_type", "unknown"),
                "dimension": faiss_stats.get("dimension", 0)
            }
        
        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {"error": str(e)}


# Global initializer instance
faiss_initializer = FaissInitializer()