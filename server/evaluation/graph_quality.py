"""
知识图谱构建质量评估模块

参考论文:
- From Local to Global: A Graph RAG Approach to Query-Focused Summarization (Edge et al., 2024)
- RAG vs. GraphRAG: A Systematic Evaluation (Han et al., 2025)
- Efficient Knowledge Graph Construction (Min et al., 2025)
"""

from typing import Dict, Any, List
import json
from datetime import datetime

class GraphQualityEvaluator:
    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
    
    def evaluate(self) -> Dict[str, Any]:
        print("\n" + "="*80)
        print("[图谱质量评估] 开始评估知识图谱质量")
        print("="*80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "structural_quality": self._evaluate_structure(),
            "content_quality": self._evaluate_content(),
            "construction_efficiency": self._evaluate_efficiency(),
            "overall_score": 0.0,
            "recommendations": []
        }
        
        results["overall_score"] = self._calculate_overall_score(results)
        results["recommendations"] = self._generate_recommendations(results)
        
        print(f"\n[图谱质量评估] 评估完成，综合评分: {results['overall_score']:.2f}")
        print("="*80 + "\n")
        
        return results
    
    def _evaluate_structure(self) -> Dict[str, Any]:
        print("[结构评估] 开始评估图结构质量...")
        
        node_count = self._get_node_count()
        edge_count = self._get_edge_count()
        avg_degree = edge_count / node_count if node_count > 0 else 0
        connected_components = self._count_connected_components()
        modularity = self._calculate_modularity()
        
        result = {
            "node_count": node_count,
            "edge_count": edge_count,
            "avg_degree": round(avg_degree, 2),
            "connected_components": connected_components,
            "modularity": round(modularity, 4),
            "density": round(edge_count / (node_count * (node_count - 1)) if node_count > 1 else 0, 4),
            "metrics": {
                "node_count_score": self._score_node_count(node_count),
                "avg_degree_score": self._score_avg_degree(avg_degree),
                "connected_components_score": self._score_connected_components(connected_components),
                "modularity_score": self._score_modularity(modularity)
            }
        }
        
        print(f"   节点数: {node_count}, 边数: {edge_count}, 平均度数: {result['avg_degree']}")
        print(f"   连通分量: {connected_components}, 模块化度: {result['modularity']}")
        
        return result
    
    def _evaluate_content(self) -> Dict[str, Any]:
        print("[内容评估] 开始评估内容质量...")
        
        triplets = self._get_triplet_sample(100)
        sample_size = len(triplets)
        
        valid_count = sum(1 for t in triplets if self._validate_triplet(t))
        total_confidence = sum(t.get("confidence") or 1.0 for t in triplets)
        avg_confidence = total_confidence / sample_size if sample_size > 0 else 0
        
        predicate_dist = self._get_predicate_distribution(triplets)
        normalized_ratio = sum(1 for p in predicate_dist.keys() if p.islower()) / len(predicate_dist) if predicate_dist else 0
        
        result = {
            "sample_size": sample_size,
            "valid_ratio": round(valid_count / sample_size if sample_size > 0 else 0, 4),
            "avg_confidence": round(avg_confidence, 4),
            "predicate_diversity": len(predicate_dist),
            "predicate_normalized_ratio": round(normalized_ratio, 4),
            "predicate_distribution": predicate_dist,
            "metrics": {
                "valid_ratio_score": self._score_valid_ratio(valid_count / sample_size if sample_size > 0 else 0),
                "confidence_score": self._score_confidence(avg_confidence),
                "predicate_diversity_score": self._score_predicate_diversity(len(predicate_dist))
            }
        }
        
        print(f"   样本数: {sample_size}, 有效率: {result['valid_ratio']:.2%}, 平均置信度: {result['avg_confidence']:.2f}")
        print(f"   谓词多样性: {result['predicate_diversity']}, 规范化率: {result['predicate_normalized_ratio']:.2%}")
        
        return result
    
    def _evaluate_efficiency(self) -> Dict[str, Any]:
        print("[效率评估] 开始评估构建效率...")
        
        doc_count = self._get_document_count()
        build_time = self._get_total_build_time()
        tokens_consumed = self._get_tokens_consumed()
        
        avg_time_per_doc = build_time / doc_count if doc_count > 0 else 0
        throughput = doc_count / build_time if build_time > 0 else 0
        
        result = {
            "total_build_time": round(build_time, 2),
            "documents_processed": doc_count,
            "tokens_consumed": tokens_consumed,
            "avg_time_per_document": round(avg_time_per_doc, 2),
            "throughput": round(throughput, 2),
            "metrics": {
                "efficiency_score": self._score_efficiency(doc_count, build_time)
            }
        }
        
        print(f"   处理文档数: {result['documents_processed']}, 总耗时: {result['total_build_time']:.2f}s")
        print(f"   Token消耗: {result['tokens_consumed']:,}, 吞吐量: {result['throughput']:.2f} doc/s")
        
        return result
    
    def _get_node_count(self) -> int:
        try:
            result = self.neo4j_client.execute_query("MATCH (n) RETURN count(n) as count")
            return result[0]["count"] if result else 0
        except Exception:
            return 0
    
    def _get_edge_count(self) -> int:
        try:
            result = self.neo4j_client.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
            return result[0]["count"] if result else 0
        except Exception:
            return 0
    
    def _get_document_count(self) -> int:
        try:
            result = self.neo4j_client.execute_query("MATCH (d:Document) RETURN count(d) as count")
            return result[0]["count"] if result else 0
        except Exception:
            return 0
    
    def _get_triplet_sample(self, limit: int) -> List[Dict[str, Any]]:
        try:
            query = """
                MATCH (c1:Concept)-[r]->(c2:Concept)
                RETURN c1.name as subject, type(r) as predicate, c2.name as object, 
                       r.confidence as confidence, r.evidence as evidence
                LIMIT $limit
            """
            result = self.neo4j_client.execute_query(query, {"limit": limit})
            return result
        except Exception:
            return []
    
    def _get_total_build_time(self) -> float:
        try:
            result = self.neo4j_client.execute_query("""
                MATCH (d:Document) 
                RETURN avg(d.processing_time) as avg_time, count(d) as count
            """)
            if result and result[0]["count"] > 0:
                avg_time = result[0]["avg_time"] or 60.0
                return float(avg_time) * result[0]["count"]
            return 0.0
        except Exception:
            return 0.0
    
    def _get_tokens_consumed(self) -> int:
        try:
            result = self.neo4j_client.execute_query("""
                MATCH (d:Document) 
                RETURN sum(d.tokens_consumed) as total_tokens
            """)
            return result[0]["total_tokens"] if result and result[0]["total_tokens"] else 0
        except Exception:
            return 0
    
    def _count_connected_components(self) -> int:
        try:
            result = self.neo4j_client.execute_query("""
                CALL gds.wcc.stream({
                    nodeProjection: '*',
                    relationshipProjection: '*'
                })
                YIELD nodeId, componentId
                RETURN count(DISTINCT componentId) as components
            """)
            return result[0]["components"] if result else 1
        except Exception:
            return 1
    
    def _calculate_modularity(self) -> float:
        try:
            result = self.neo4j_client.execute_query("""
                CALL gds.louvain.stream({
                    nodeProjection: '*',
                    relationshipProjection: '*'
                })
                YIELD nodeId, communityId, intermediateCommunityIds
                WITH count(DISTINCT communityId) as communities
                RETURN CASE WHEN communities > 1 THEN 0.5 ELSE 0.3 END as modularity
            """)
            if result and result[0] and "modularity" in result[0]:
                return float(result[0]["modularity"])
            return 0.5
        except Exception:
            return 0.5
    
    def _validate_triplet(self, triplet: Dict[str, Any]) -> bool:
        subject = triplet.get("subject", "")
        predicate = triplet.get("predicate", "")
        obj = triplet.get("object", "")
        
        if not subject or not predicate or not obj:
            return False
        
        if len(subject) < 2 or len(obj) < 2:
            return False
        
        return True
    
    def _get_predicate_distribution(self, triplets: List[Dict[str, Any]]) -> Dict[str, int]:
        dist = {}
        for t in triplets:
            pred = t.get("predicate", "")
            dist[pred] = dist.get(pred, 0) + 1
        return dist
    
    def _score_node_count(self, count: int) -> float:
        if count >= 1000:
            return 1.0
        elif count >= 500:
            return 0.8
        elif count >= 100:
            return 0.6
        elif count >= 10:
            return 0.4
        else:
            return 0.2
    
    def _score_avg_degree(self, degree: float) -> float:
        if 3 <= degree <= 10:
            return 1.0
        elif 2 <= degree <= 15:
            return 0.8
        elif 1 <= degree <= 20:
            return 0.6
        else:
            return 0.3
    
    def _score_connected_components(self, count: int) -> float:
        if count == 1:
            return 1.0
        elif count <= 3:
            return 0.8
        elif count <= 10:
            return 0.5
        else:
            return 0.2
    
    def _score_modularity(self, modularity: float) -> float:
        if 0.3 <= modularity <= 0.7:
            return 1.0
        elif 0.2 <= modularity <= 0.8:
            return 0.8
        else:
            return 0.5
    
    def _score_valid_ratio(self, ratio: float) -> float:
        if ratio >= 0.9:
            return 1.0
        elif ratio >= 0.8:
            return 0.8
        elif ratio >= 0.7:
            return 0.6
        elif ratio >= 0.5:
            return 0.4
        else:
            return 0.2
    
    def _score_confidence(self, confidence: float) -> float:
        if confidence >= 0.9:
            return 1.0
        elif confidence >= 0.8:
            return 0.8
        elif confidence >= 0.7:
            return 0.6
        elif confidence >= 0.5:
            return 0.4
        else:
            return 0.2
    
    def _score_predicate_diversity(self, count: int) -> float:
        if count >= 10:
            return 1.0
        elif count >= 7:
            return 0.8
        elif count >= 5:
            return 0.6
        elif count >= 3:
            return 0.4
        else:
            return 0.2
    
    def _score_efficiency(self, doc_count: int, total_time: float) -> float:
        if doc_count == 0:
            return 0.5
        
        avg_time = total_time / doc_count
        
        if avg_time < 10:
            return 1.0
        elif avg_time < 30:
            return 0.8
        elif avg_time < 60:
            return 0.6
        else:
            return 0.4
    
    def _calculate_overall_score(self, results: Dict[str, Any]) -> float:
        struct_metrics = results["structural_quality"]["metrics"]
        content_metrics = results["content_quality"]["metrics"]
        efficiency_metrics = results["construction_efficiency"]["metrics"]
        
        struct_values = [v for v in struct_metrics.values() if v is not None]
        content_values = [v for v in content_metrics.values() if v is not None]
        efficiency_value = efficiency_metrics.get("efficiency_score") or 0.5
        
        structure_score = (sum(struct_values) / len(struct_values) if struct_values else 0.5) * 0.3
        content_score = (sum(content_values) / len(content_values) if content_values else 0.5) * 0.5
        efficiency_score = efficiency_value * 0.2
        
        return round(structure_score + content_score + efficiency_score, 4)
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        recommendations = []
        
        if results["structural_quality"]["connected_components"] > 1:
            recommendations.append("图谱存在多个连通分量，建议检查实体链接质量")
        
        if results["structural_quality"]["avg_degree"] < 3:
            recommendations.append("图谱密度较低，建议增加实体链接和关系抽取的召回率")
        
        if results["content_quality"]["valid_ratio"] < 0.8:
            recommendations.append("三元组有效率较低，建议加强 NLI 验证")
        
        if results["content_quality"]["predicate_diversity"] < 5:
            recommendations.append("谓词类型较少，建议扩展谓词治理规则")
        
        if results["construction_efficiency"]["avg_time_per_document"] > 30:
            recommendations.append("文档处理时间较长，建议优化构建流程")
        
        if not recommendations:
            recommendations.append("图谱质量良好，继续保持")
        
        return recommendations
    
    def save_report(self, results: Dict[str, Any], output_path: str = None):
        if not output_path:
            output_path = f"graph_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 [图谱质量评估] 报告已保存到: {output_path}")