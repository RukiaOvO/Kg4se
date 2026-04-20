"""FAISS vector store for efficient similarity search.

配置统一从 config.settings 读取
"""

import os
import logging
import pickle
import numpy as np
from typing import List, Dict, Optional, Tuple, Any

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from config import settings

logger = logging.getLogger("infra.faiss_store")


class SearchResult:
    """Search result with metadata."""
    
    def __init__(
        self,
        id: str,
        similarity: float,
        metadata: Dict[str, Any]
    ):
        self.id = id
        self.similarity = similarity
        self.metadata = metadata


class FaissStore:
    """FAISS-based vector storage for efficient similarity search."""
    
    def __init__(
        self,
        dimension: Optional[int] = None,
        index_type: Optional[str] = None,
        index_path: Optional[str] = None
    ):
        """
        Initialize FAISS store.
        
        Args:
            dimension: Vector dimension (default: from settings)
            index_type: Index type (default: from settings)
            index_path: Path to load existing index from (default: from settings)
        """
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available, using simple in-memory storage")
            self._use_fallback = True
            self._vectors: List[List[float]] = []
            self._ids: List[str] = []
            self._metadata: List[Dict] = []
            self.index_path = index_path or settings.faiss_index_path
            return
        
        self._use_fallback = False
        self.dimension = dimension or settings.embedding_dimension
        self.index_type = index_type or settings.faiss_index_type
        self.index_path = index_path or settings.faiss_index_path
        
        self.index = self._create_index(self.index_type)
        self.id_to_metadata: Dict[str, Dict] = {}
        
        if self.index_path and os.path.exists(self.index_path + ".index"):
            self.load_index()
            logger.info(f"Loaded existing FAISS index from {self.index_path}")
    
    def _create_index(self, index_type: str):
        """Create FAISS index based on type."""
        if index_type == "hnsw":
            index = faiss.IndexHNSWFlat(self.dimension, 32)
            index.hnsw.efConstruction = 40
            index.hnsw.efSearch = 16
        elif index_type == "ivf":
            nlist = 100
            quantizer = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            index.nprobe = 10
        elif index_type == "pq":
            index = faiss.IndexPQ(self.dimension, 16, 8)
        else:
            index = faiss.IndexFlatL2(self.dimension)
        
        logger.info(f"Created {index_type} index with dimension {self.dimension}")
        return index
    
    def insert(
        self,
        embeddings: List[List[float]],
        ids: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> bool:
        """Insert vectors into the index."""
        if self._use_fallback:
            return self._fallback_insert(embeddings, ids, metadata_list)
        
        try:
            np_embeddings = np.array(embeddings, dtype=np.float32)
            
            if isinstance(self.index, faiss.IndexIVFFlat) and not self.index.is_trained:
                self.index.train(np_embeddings)
            
            self.index.add(np_embeddings)
            
            if metadata_list is None:
                metadata_list = [{}] * len(ids)
            
            for id_str, metadata in zip(ids, metadata_list):
                self.id_to_metadata[id_str] = metadata
            
            logger.info(f"Inserted {len(embeddings)} vectors into FAISS index")
            return True
        
        except Exception as e:
            logger.error(f"Failed to insert vectors: {e}")
            return False
    
    def _fallback_insert(
        self,
        embeddings: List[List[float]],
        ids: List[str],
        metadata_list: Optional[List[Dict]] = None
    ) -> bool:
        """Fallback insertion for when FAISS is not available."""
        try:
            if metadata_list is None:
                metadata_list = [{}] * len(ids)
            
            for id_str, embedding, metadata in zip(ids, embeddings, metadata_list):
                if id_str not in self._ids:
                    self._ids.append(id_str)
                    self._vectors.append(embedding)
                    self._metadata.append(metadata)
                else:
                    idx = self._ids.index(id_str)
                    self._vectors[idx] = embedding
                    self._metadata[idx] = metadata
            
            logger.info(f"Inserted {len(embeddings)} vectors into fallback storage")
            return True
        except Exception as e:
            logger.error(f"Failed to insert vectors (fallback): {e}")
            return False
    
    def search(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """Search for similar vectors."""
        search_top_k = top_k or settings.faiss_search_top_k
        search_threshold = threshold or settings.faiss_search_threshold
        
        if self._use_fallback:
            return self._fallback_search(query_embedding, search_top_k, search_threshold)
        
        try:
            np_query = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(np_query, search_top_k)
            
            results = []
            for i in range(len(indices[0])):
                idx = indices[0][i]
                if idx == -1:
                    continue
                
                distance = distances[0][i]
                similarity = 1.0 / (1.0 + distance)
                
                if similarity < search_threshold:
                    continue
                
                result_id = str(idx)
                metadata = self.id_to_metadata.get(result_id, {})
                
                results.append(SearchResult(
                    id=result_id,
                    similarity=similarity,
                    metadata=metadata
                ))
            
            results.sort(key=lambda x: x.similarity, reverse=True)
            return results
        
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            logger.error(f"  Query embedding length: {len(query_embedding) if query_embedding else 0}")
            logger.error(f"  Index dimension: {self.dimension}")
            logger.error(f"  Index vector count: {self.index.ntotal if hasattr(self.index, 'ntotal') else 'unknown'}")
            import traceback
            logger.debug(f"  Traceback: {traceback.format_exc()}")
            return []
    
    def _fallback_search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[SearchResult]:
        """Fallback search using cosine similarity."""
        try:
            results = []
            
            for idx, (vec, id_str, metadata) in enumerate(zip(
                self._vectors, self._ids, self._metadata
            )):
                similarity = self._cosine_similarity(query_embedding, vec)
                if similarity >= threshold:
                    results.append(SearchResult(
                        id=id_str,
                        similarity=similarity,
                        metadata=metadata
                    ))
            
            results.sort(key=lambda x: x.similarity, reverse=True)
            return results[:top_k]
        
        except Exception as e:
            logger.error(f"Failed to search vectors (fallback): {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by ID."""
        logger.warning("FAISS deletion not implemented, skipping")
        return True
    
    def update(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadata_list: Optional[List[Dict]] = None
    ) -> bool:
        """Update existing vectors."""
        if self._use_fallback:
            return self._fallback_insert(embeddings, ids, metadata_list)
        
        logger.warning("FAISS update: using insert (may create duplicates)")
        return self.insert(embeddings, ids, metadata_list)
    
    def save_index(self, path: Optional[str] = None) -> bool:
        """Save index to disk."""
        save_path = path or self.index_path
        
        if self._use_fallback:
            return self._fallback_save(save_path)
        
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            faiss.write_index(self.index, save_path + ".index")
            
            metadata_path = save_path + ".metadata"
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.id_to_metadata, f)
            
            logger.info(f"Saved FAISS index to {save_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False
    
    def _fallback_save(self, path: str) -> bool:
        """Save fallback data to disk."""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            data = {
                'vectors': self._vectors,
                'ids': self._ids,
                'metadata': self._metadata
            }
            
            with open(path + ".fallback", 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"Saved fallback index to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save fallback index: {e}")
            return False
    
    def load_index(self, path: Optional[str] = None) -> bool:
        """Load index from disk."""
        load_path = path or self.index_path
        
        if self._use_fallback:
            return self._fallback_load(load_path)
        
        try:
            index_path = load_path + ".index"
            metadata_path = load_path + ".metadata"
            
            if os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'rb') as f:
                    self.id_to_metadata = pickle.load(f)
            
            logger.info(f"Loaded FAISS index from {load_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
    
    def _fallback_load(self, path: str) -> bool:
        """Load fallback data from disk."""
        try:
            fallback_path = path + ".fallback"
            
            if os.path.exists(fallback_path):
                with open(fallback_path, 'rb') as f:
                    data = pickle.load(f)
                
                self._vectors = data.get('vectors', [])
                self._ids = data.get('ids', [])
                self._metadata = data.get('metadata', [])
            
            logger.info(f"Loaded fallback index from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load fallback index: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        if self._use_fallback:
            return {
                'index_type': 'fallback',
                'vector_count': len(self._vectors),
                'dimension': self.dimension if hasattr(self, 'dimension') else 0
            }
        
        return {
            'index_type': self.index_type,
            'vector_count': self.index.ntotal if hasattr(self.index, 'ntotal') else 0,
            'dimension': self.dimension,
            'metadata_count': len(self.id_to_metadata)
        }
    
    def clear(self):
        """Clear all data from the index."""
        if self._use_fallback:
            self._vectors = []
            self._ids = []
            self._metadata = []
        else:
            self.index = self._create_index(self.index_type)
            self.id_to_metadata = {}
        
        logger.info("Cleared FAISS index")


# 全局 FAISS store 实例
faiss_store = FaissStore()


