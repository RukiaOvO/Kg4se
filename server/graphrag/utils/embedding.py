"""
向量化工具

文本嵌入、相似度计算

配置统一从 config.settings 读取
"""

import logging
import numpy as np
from typing import List, Optional
from functools import lru_cache
from openai import OpenAI

from config import settings

logger = logging.getLogger("graphrag.embedding")


def get_default_embedding_model() -> str:
    """
    获取默认嵌入模型名称（从 settings 读取）
    
    Returns:
        嵌入模型名称
    """
    return settings.embedding_model


def get_default_embedding_dimension() -> int:
    """
    获取默认嵌入向量维度（从 settings 读取）
    
    Returns:
        向量维度
    """
    return settings.embedding_dimension


def get_embedding(text: str, model: Optional[str] = None) -> List[float]:
    """
    获取文本的向量表示
    
    Args:
        text: 输入文本
        model: 嵌入模型名称（如果为 None，从 settings 读取）
    
    Returns:
        向量表示
    """
    embedding_model = model or settings.embedding_model
    embedding_dim = settings.embedding_dimension
    api_key = settings.embedding_api_key
    base_url = settings.embedding_base_url
    
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding")
        return [0.0] * embedding_dim
    
    try:
        if not api_key:
            logger.warning("No embedding API key found, returning zero vector")
            return [0.0] * embedding_dim
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None
        )
        
        response = client.embeddings.create(
            input=text,
            model=embedding_model
        )
        
        embedding = response.data[0].embedding
        logger.debug(f"Generated embedding for text (length={len(text)}, dim={len(embedding)}, model={embedding_model})")
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return [0.0] * embedding_dim


def batch_embed(
    texts: List[str],
    model: Optional[str] = None,
    batch_size: int = 100
) -> List[List[float]]:
    """
    批量向量化
    
    Args:
        texts: 文本列表
        model: 嵌入模型名称（如果为 None，从 settings 读取）
        batch_size: 批量大小
    
    Returns:
        向量列表
    """
    embedding_model = model or settings.embedding_model
    embedding_dim = settings.embedding_dimension
    api_key = settings.embedding_api_key
    base_url = settings.embedding_base_url
    
    if not texts:
        return []
    
    embeddings = []
    
    try:
        if not api_key:
            logger.warning("No embedding API key found, returning zero vectors")
            return [[0.0] * embedding_dim for _ in texts]
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url if base_url else None
        )
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            valid_batch = [(idx, text) for idx, text in enumerate(batch) if text and text.strip()]
            
            if not valid_batch:
                embeddings.extend([[0.0] * embedding_dim for _ in batch])
                continue
            
            valid_texts = [text for _, text in valid_batch]
            valid_indices = [idx for idx, _ in valid_batch]
            
            try:
                response = client.embeddings.create(
                    input=valid_texts,
                    model=embedding_model
                )
                
                result_map = {idx: emb.embedding for idx, emb in enumerate(response.data)}
                
                batch_embeddings = []
                for orig_idx in range(len(batch)):
                    if orig_idx in valid_indices:
                        result_idx = valid_indices.index(orig_idx)
                        batch_embeddings.append(result_map[result_idx])
                    else:
                        batch_embeddings.append([0.0] * embedding_dim)
                
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                embeddings.extend([[0.0] * embedding_dim for _ in batch])
        
        return embeddings
        
    except Exception as e:
        logger.error(f"Failed to batch embed: {e}")
        return [[0.0] * embedding_dim for _ in texts]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """计算余弦相似度"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    dot_product = np.dot(v1, v2)
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def euclidean_distance(vec1: List[float], vec2: List[float]) -> float:
    """计算欧氏距离"""
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    return float(np.linalg.norm(v1 - v2))


def top_k_similar(
    query_vec: List[float],
    candidate_vecs: List[List[float]],
    k: int = 10
) -> List[tuple[int, float]]:
    """找出最相似的 K 个向量"""
    similarities = [
        (i, cosine_similarity(query_vec, vec))
        for i, vec in enumerate(candidate_vecs)
    ]
    
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]


@lru_cache(maxsize=1000)
def cached_embedding(text: str, model: Optional[str] = None) -> tuple:
    """带缓存的向量化"""
    embedding_model = model or settings.embedding_model
    embedding = get_embedding(text, embedding_model)
    return tuple(embedding)


__all__ = [
    "get_embedding",
    "batch_embed",
    "cosine_similarity",
    "euclidean_distance",
    "top_k_similar",
    "cached_embedding",
    "get_default_embedding_model",
    "get_default_embedding_dimension"
]