"""
阶段 3: 论断抽取 (Claim Extraction)

从 Chunk 中抽取作者的论断与观点，并识别论断间关系
"""

import logging
import json
import hashlib
import re
from pathlib import Path
from typing import List, Tuple, Optional
from graphrag.models.chunk import ChunkMetadata
from graphrag.models.claim import Claim, ClaimRelation
from graphrag.config import get_config
from services.config_service import config_service
from infra.ai_providers import AIProviderFactory
from graphrag.utils.evidence_aligner import align_evidence
from graphrag.utils.claim_deduplicator import deduplicate_claims, compute_text_hash
from graphrag.utils.nli_verifier import NLIVerifier
from prompts import PromptManager

logger = logging.getLogger("graphrag.stage3")


class ClaimExtractor:
    """
    论断抽取器
    
    使用 LLM 提取论断与关系
    """
    
    def __init__(self, enable_nli: bool = False):
        self.config = get_config()
        self.client = None
        self.enable_nli = enable_nli
        
        prompt_manager = PromptManager()
        self.prompt_template = prompt_manager.get("graphrag", "claim_extraction")
        
        if not self.prompt_template:
            self.prompt_template = self._default_prompt()
        
        try:
            ai_config = config_service.get_ai_provider_config()
            provider = ai_config["provider"]
            api_key = ai_config["api_key"]
            model = ai_config["model"]
            base_url = ai_config["base_url"]
            
            logger.info(f"[ClaimExtractor] AI配置: provider={provider}, model={model}, api_key={'已配置' if api_key else '未配置'}")
            
            if provider != "mock" and api_key:
                self.client = AIProviderFactory.create_client(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url
                )
                logger.info(f"[ClaimExtractor] AI客户端初始化成功: provider={provider}, model={model}")
            else:
                logger.warning(f"[ClaimExtractor] AI客户端未初始化: provider={provider}, api_key={'已配置' if api_key else '未配置'}")
        except Exception as e:
            logger.error(f"[ClaimExtractor] AI客户端初始化失败: {e}", exc_info=True)
        
        self.nli_verifier = NLIVerifier(client=self.client) if self.enable_nli else None
        
        nli_status = "enabled" if self.enable_nli else "disabled"
        logger.info(f"[ClaimExtractor] 初始化完成 (NLI验证: {nli_status})")
    
    def extract(
        self, 
        chunk: ChunkMetadata,
        adjacent_chunks: Optional[List[ChunkMetadata]] = None
    ) -> Tuple[List[Claim], List[ClaimRelation]]:
        """
        从 Chunk 中抽取论断与关系（P2 优化版本）
        
        Args:
            chunk: 输入 Chunk
            adjacent_chunks: 相邻 Chunks（用于篇章感知预处理，可选）
        
        Returns:
            (claims, relations)
        """
        logger.debug(f"开始论断抽取: chunk_id={chunk.id}")
        
        # P2 优化：篇章感知预处理 - 复用 stage0 结果
        # 如果有相邻 chunks，构建上下文增强的文本
        context_text = self._build_context_aware_text(chunk, adjacent_chunks)
        
        # 根据 coref_mode 决定是否使用 resolved_text
        # 规范：local/alias_only 模式禁止使用替换后的文本，避免污染下游
        use_resolved_text = (
            chunk.resolved_text and 
            chunk.coref_mode == "rewrite"
        )
        text = chunk.resolved_text if use_resolved_text else chunk.text
        
        if not self.client:
            logger.debug("Using mock mode, returning empty results")
            return [], []
        
        try:
            prompt_text = context_text if context_text else text
            
            logger.debug(f"[Stage3] prompt_template 长度: {len(self.prompt_template)}")
            logger.debug(f"[Stage3] prompt_text 长度: {len(prompt_text)}")
            
            prompt = self.prompt_template.format(input_text=prompt_text)
            
            logger.debug(f"[Stage3] 渲染后 prompt 长度: {len(prompt)}")
            logger.debug(f"[Stage3] 渲染后 prompt 前100字符: {prompt[:100]}")
            
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的知识图谱构建专家，擅长从学术文本中提取论断与观点。请严格按照 JSON 格式返回结果，必须包含 claims 数组。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            raw_content = self.client.chat_completion(
                messages=messages,
                temperature=0.3,
                json_mode=True
            )
            
            if not raw_content:
                logger.error("[Stage3] LLM 返回空内容")
                return [], []
                
            logger.info(f"[Stage3] LLM原始响应长度: {len(raw_content)} 字符")
            logger.debug(f"[Stage3] LLM原始响应: {raw_content[:1000]}")
            
            try:
                result = json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"[Stage3] JSON解析失败: {e}")
                logger.error(f"[Stage3] 原始内容: {raw_content[:500]}")
                
                import re
                json_match = re.search(r'\{[\s\S]*\}', raw_content)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        logger.info(f"[Stage3] 从文本中提取JSON成功")
                    except:
                        logger.error(f"[Stage3] 无法从文本中提取有效JSON")
                        return [], []
                else:
                    return [], []
            
            raw_claims = result.get("claims", [])
            if not raw_claims and "entities" in result:
                logger.warning(f"[Stage3] LLM返回了entities字段而非claims字段，尝试转换")
                entities = result.get("entities", [])
                logger.debug(f"[Stage3] entities数量: {len(entities)}")
                raw_claims = []
                for entity in entities:
                    if isinstance(entity, dict) and "text" in entity:
                        raw_claims.append(entity)
                    elif isinstance(entity, str):
                        raw_claims.append({"text": entity, "type": "fact", "confidence": 0.7})
            
            raw_relations = result.get("relations", [])
            
            logger.info(f"[Stage3] 解析结果: claims={len(raw_claims)}, relations={len(raw_relations)}")
            if raw_claims:
                claim_types = [c.get("type", "unknown") for c in raw_claims[:5]]
                logger.debug(f"[Stage3] 前5个claim类型: {claim_types}")
            
            # 4. 构造 Claim 对象（P0 优化：证据对齐 + 属性检测）
            claims = []
            skipped_short = 0
            for idx, raw_claim in enumerate(raw_claims):
                claim_text = raw_claim.get("text", "").strip()
                if not claim_text or len(claim_text) < 20:
                    skipped_short += 1
                    continue
                
                logger.debug(f"[Stage3] 处理论断 {idx+1}/{len(raw_claims)}: {claim_text[:30]}...")
                
                claim_id = hashlib.sha256(
                    f"{chunk.id}:{idx}:{claim_text}".encode()
                ).hexdigest()[:16]
                
                # 4.1 证据硬对齐（P0 核心功能）
                llm_span = raw_claim.get("evidence_span", None)
                if isinstance(llm_span, list) and len(llm_span) >= 2:
                    llm_span = tuple(llm_span[:2])
                else:
                    llm_span = None
                
                # 执行证据对齐
                evidence_span, match_ratio = align_evidence(
                    claim_text=claim_text,
                    source_text=text,
                    llm_span=llm_span,
                    min_match_ratio=0.6
                )
                
                # 如果匹配度太低，降低置信度或跳过
                if match_ratio < 0.6:
                    logger.warning(f"证据对齐失败: claim_text='{claim_text[:50]}...', match_ratio={match_ratio:.3f}")
                    # 不跳过，但降低置信度
                    adjusted_confidence = raw_claim.get("confidence", 0.7) * match_ratio
                else:
                    adjusted_confidence = raw_claim.get("confidence", 0.7)
                
                modality = self._detect_modality(claim_text)
                polarity = self._detect_polarity(claim_text)
                certainty = self._compute_certainty(claim_text, adjusted_confidence, modality)
                
                if self.enable_nli and self.nli_verifier:
                    nli_result = self.nli_verifier.verify_claim(
                        claim_text=claim_text,
                        source_text=text,
                        max_retries=1
                    )
                    
                    if nli_result["label"] == "entailment":
                        adjusted_confidence = min(1.0, adjusted_confidence * 1.1)
                    elif nli_result["label"] == "contradiction":
                        adjusted_confidence = adjusted_confidence * 0.5
                    elif nli_result["label"] == "neutral":
                        adjusted_confidence = adjusted_confidence * 0.9
                    
                    nli_confidence = nli_result.get("confidence", 0.5)
                    certainty = (certainty + nli_confidence) / 2.0
                    
                    logger.debug(
                        f"论断验证: claim='{claim_text[:50]}...', "
                        f"NLI={nli_result['label']}({nli_confidence:.2f}), "
                        f"最终置信度={adjusted_confidence:.2f}"
                    )
                
                # 4.3 计算规范化文本哈希（用于去重）
                normalized_text_hash = compute_text_hash(claim_text)
                
                # 映射 claim_type 到有效值
                valid_claim_types = {"fact", "hypothesis", "conclusion", "definition", "finding", "recommendation"}
                claim_type_raw = raw_claim.get("type", "fact")
                claim_type = claim_type_raw if claim_type_raw in valid_claim_types else "fact"
                
                claim = Claim(
                    id=f"claim_{claim_id}",
                    text=claim_text,
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.id,
                    sentence_ids=chunk.sentence_ids,
                    evidence_span=evidence_span,
                    section_path=chunk.section_path,
                    claim_type=claim_type,
                    confidence=adjusted_confidence,
                    modality=modality,
                    polarity=polarity,
                    certainty=certainty,
                    normalized_text_hash=normalized_text_hash,
                    build_version=chunk.build_version
                )
                claims.append(claim)
            
            logger.debug(f"[Stage3] 有效论断数量: {len(claims)}, 跳过过短: {skipped_short}")
            
            # 4.4 去重与规范化（P0 核心功能）
            if claims:
                logger.debug(f"[Stage3] 开始去重: {len(claims)} 个论断")
                claims, merged_map = deduplicate_claims(
                    claims,
                    enable_soft_cluster=True,
                    similarity_threshold=0.92
                )
                if merged_map:
                    logger.info(f"去重完成: 合并了 {sum(len(v) for v in merged_map.values())} 个重复/相似论断")
            
            # 5. 构造 ClaimRelation 对象（P2 优化：NLI 验证）
            relations = []
            for raw_rel in raw_relations:
                source_idx = raw_rel.get("source_claim_index", -1)
                target_idx = raw_rel.get("target_claim_index", -1)
                
                if source_idx < 0 or target_idx < 0 or source_idx >= len(claims) or target_idx >= len(claims):
                    continue
                
                source_claim = claims[source_idx]
                target_claim = claims[target_idx]
                
                # P2 优化：NLI 验证关系
                relation_type = raw_rel.get("relation_type", "SUPPORTS")
                base_confidence = raw_rel.get("confidence", 0.7)
                
                # 使用 NLI 验证关系是否正确
                if self.enable_nli and self.nli_verifier:
                    relation_context = raw_rel.get("evidence") or text
                    nli_relation_result = self.nli_verifier.verify_relation(
                        source_claim=source_claim.text,
                        target_claim=target_claim.text,
                        relation_type=relation_type,
                        context=relation_context,
                        max_retries=2  # 多头验证
                    )
                    
                    # 根据 NLI 验证结果调整关系置信度
                    if nli_relation_result["is_valid"]:
                        # 关系有效，提高置信度
                        final_confidence = min(1.0, base_confidence * 1.1)
                    else:
                        # 关系无效，降低置信度
                        final_confidence = base_confidence * 0.6
                else:
                    # 不使用 NLI 验证时，直接使用基础置信度
                    final_confidence = base_confidence
                
                # 如果置信度太低，跳过该关系
                if final_confidence < 0.4:
                    logger.debug(
                        f"跳过低置信度关系: {source_claim.text[:30]}... -> "
                        f"{target_claim.text[:30]}... ({relation_type}), "
                        f"置信度={final_confidence:.2f}"
                    )
                    continue
                
                rel_id = hashlib.sha256(
                    f"{source_claim.id}:{target_claim.id}:{relation_type}".encode()
                ).hexdigest()[:16]
                
                relation = ClaimRelation(
                    id=f"rel_{rel_id}",
                    source_claim_id=source_claim.id,
                    target_claim_id=target_claim.id,
                    relation_type=relation_type,
                    confidence=final_confidence,
                    strength=raw_rel.get("strength"),
                    evidence=raw_rel.get("evidence"),
                    build_version=chunk.build_version
                )
                relations.append(relation)
                
                logger.debug(
                    f"关系验证: {relation_type}, "
                    f"NLI有效={'N/A' if not (self.enable_nli and self.nli_verifier) else nli_relation_result.get('is_valid', 'N/A')}, "
                    f"最终置信度={final_confidence:.2f}"
                )
            
            logger.info(f"论断抽取完成: chunk_id={chunk.id}, claims={len(claims)}, relations={len(relations)}")
            return claims, relations
            
        except json.JSONDecodeError as e:
            logger.error(f"[Stage3] JSON解析错误: {e}")
            logger.error(f"[Stage3] 错误位置: line={e.lineno}, col={e.colno}")
            logger.error(f"[Stage3] 错误内容: {e.msg}")
            import traceback
            logger.error(f"[Stage3] 堆栈跟踪:\n{traceback.format_exc()}")
            return [], []
        except KeyError as e:
            import traceback
            logger.error(f"[Stage3] KeyError: {e}")
            logger.error(f"[Stage3] KeyError 堆栈:\n{traceback.format_exc()}")
            return [], []
        except Exception as e:
            logger.error(f"[Stage3] 论断抽取失败: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[Stage3] 堆栈跟踪:\n{traceback.format_exc()}")
            return [], []
    
    def _detect_modality(self, text: str) -> Optional[str]:
        """
        检测语气类型（简化版：基于关键词）
        
        Args:
            text: 论断文本
        
        Returns:
            "assertive" | "hedged" | "speculative" | None
        """
        text_lower = text.lower()
        
        # 谨慎语气（hedged）关键词
        hedge_words = [
            "可能", "或许", "似乎", "倾向于", "大概", "也许", "或许",
            "可能", "maybe", "perhaps", "might", "could", "possibly",
            "appears", "seems", "suggests", "indicates"
        ]
        
        # 推测语气（speculative）关键词
        speculative_words = [
            "假设", "推测", "猜想", "如果", "倘若", "假如",
            "hypothesis", "speculate", "assume", "presume", "conjecture"
        ]
        
        # 检查是否包含谨慎词
        for word in hedge_words:
            if word in text_lower:
                return "hedged"
        
        # 检查是否包含推测词
        for word in speculative_words:
            if word in text_lower:
                return "speculative"
        
        # 默认断言语气
        return "assertive"
    
    def _detect_polarity(self, text: str) -> Optional[str]:
        """
        检测极性（简化版：基于否定词）
        
        Args:
            text: 论断文本
        
        Returns:
            "positive" | "negative" | "neutral" | None
        """
        text_lower = text.lower()
        
        # 否定词列表
        negative_words = [
            "不", "非", "无", "未", "没有", "缺乏", "缺失", "失败", "错误",
            "not", "no", "none", "without", "lack", "fail", "error", "wrong",
            "never", "neither", "nor"
        ]
        
        # 检查否定词
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if negative_count > 0:
            # 检查是否有双重否定（可能表示肯定）
            if "不" in text_lower and "不" in text_lower[text_lower.find("不") + 1:]:
                return "positive"
            return "negative"
        
        return "positive"  # 默认肯定
    
    def _compute_certainty(self, text: str, base_confidence: float, modality: Optional[str]) -> float:
        """
        计算确定性分数（考虑不确定性词汇的影响）
        
        Args:
            text: 论断文本
            base_confidence: 基础置信度
            modality: 语气类型
        
        Returns:
            确定性分数 [0.0-1.0]
        """
        certainty = base_confidence
        
        # 根据语气类型调整
        if modality == "hedged":
            certainty -= 0.2  # 谨慎语气降低确定性
        elif modality == "speculative":
            certainty -= 0.3  # 推测语气进一步降低
        
        # 检查不确定性修饰词
        uncertainty_modifiers = [
            "可能", "或许", "似乎", "大概", "也许",
            "maybe", "perhaps", "possibly", "likely", "unlikely"
        ]
        
        text_lower = text.lower()
        for modifier in uncertainty_modifiers:
            if modifier in text_lower:
                certainty -= 0.1
                break
        
        # 确保在有效范围内
        return max(0.0, min(1.0, certainty))
    
    def _build_context_aware_text(
        self,
        chunk: ChunkMetadata,
        adjacent_chunks: Optional[List[ChunkMetadata]]
    ) -> Optional[str]:
        """
        P2 优化：篇章感知预处理 - 复用 stage0 结果
        
        构建包含相邻 chunk 上下文的增强文本
        
        Args:
            chunk: 当前 Chunk
            adjacent_chunks: 相邻 Chunks（前一个和后一个）
        
        Returns:
            增强后的文本（如果提供了相邻 chunks），否则返回 None
        """
        if not adjacent_chunks:
            return None
        
        # 构建上下文文本
        context_parts = []
        
        # 前一个 chunk（如果有）
        prev_chunks = [c for c in adjacent_chunks if c.chunk_index < chunk.chunk_index]
        if prev_chunks:
            prev_chunk = max(prev_chunks, key=lambda c: c.chunk_index)
            use_prev_resolved = (
                prev_chunk.resolved_text and 
                prev_chunk.coref_mode == "rewrite"
            )
            prev_text = prev_chunk.resolved_text if use_prev_resolved else prev_chunk.text
            context_parts.append(f"[前文上下文]\n{prev_text[-200:]}\n")  # 只取最后200字符
        
        # 当前 chunk
        use_resolved = (
            chunk.resolved_text and 
            chunk.coref_mode == "rewrite"
        )
        current_text = chunk.resolved_text if use_resolved else chunk.text
        context_parts.append(f"[当前文本]\n{current_text}\n")
        
        # 后一个 chunk（如果有）
        next_chunks = [c for c in adjacent_chunks if c.chunk_index > chunk.chunk_index]
        if next_chunks:
            next_chunk = min(next_chunks, key=lambda c: c.chunk_index)
            use_next_resolved = (
                next_chunk.resolved_text and 
                next_chunk.coref_mode == "rewrite"
            )
            next_text = next_chunk.resolved_text if use_next_resolved else next_chunk.text
            context_parts.append(f"[后文上下文]\n{next_text[:200]}\n")  # 只取前200字符
        
        enhanced_text = "\n".join(context_parts)
        logger.debug(f"篇章感知预处理: chunk_id={chunk.id}, 上下文长度={len(enhanced_text)}")
        
        return enhanced_text
    
    def _default_prompt(self) -> str:
        """默认 Prompt 模板"""
        return """你是一个专业的知识图谱构建专家，擅长从学术文本中提取论断与观点。

从以下文本中提取作者的主张、论断或命题，并识别它们之间的关系。

文本:
{text}

要求:
1. 提取论断：识别作者的核心主张（fact/hypothesis/conclusion）
2. 识别关系：论断之间的逻辑关系（SUPPORTS/CONTRADICTS/CAUSES/COMPARES_WITH/CONDITIONS/PURPOSE）
3. 置信度评估：为每个论断和关系给出 0.0-1.0 的置信度分数
4. 证据定位：标记论断在原文中的位置（字符偏移量）

返回 JSON 格式:
{{
  "claims": [
    {{
      "text": "论断原文",
      "type": "fact | hypothesis | conclusion",
      "confidence": 0.0-1.0,
      "evidence_span": [start_char, end_char]
    }}
  ],
  "relations": [
    {{
      "source_claim_index": 0,
      "target_claim_index": 1,
      "relation_type": "SUPPORTS | CONTRADICTS | CAUSES | ...",
      "confidence": 0.0-1.0,
      "evidence": "支撑此关系的原文片段（可选）"
    }}
  ]
}}"""


__all__ = ["ClaimExtractor"]

