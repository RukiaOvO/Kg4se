"""Graph query routes."""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from infra.neo4j_client import neo4j_client
from models.graph import GraphQuery, GraphResponse, Node, Edge, NodeCreate, NodeUpdate, EdgeCreate, EdgeUpdate

router = APIRouter(prefix="/graph", tags=["graph"])


def _clean_properties(props: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean properties dict to ensure all values are JSON-serializable.
    Converts Neo4j DateTime and Python datetime objects to ISO format strings.
    """
    clean_props = {}
    for k, v in props.items():
        if hasattr(v, 'isoformat'):
            # Python datetime/date/time objects
            clean_props[k] = v.isoformat()
        elif hasattr(v, 'to_native'):
            # Neo4j DateTime objects
            native_val = v.to_native()
            clean_props[k] = native_val.isoformat() if hasattr(native_val, 'isoformat') else str(v)
        else:
            clean_props[k] = v
    return clean_props


@router.get("/visualize")
async def visualize_graph(
    limit: int = Query(500, ge=10, le=10000, description="Maximum nodes to return"),
    edge_limit: int = Query(1000, ge=10, le=50000, description="Maximum edges to return"),
    node_type: Optional[str] = Query(None, description="Filter by node type (Concept, Document, etc)"),
):
    """
    Get knowledge graph data optimized for visualization.
    
    Returns nodes and edges in a format suitable for frontend visualization libraries.
    Automatically handles Neo4j type conversions (DateTime, Node objects, etc).
    """
    try:
        # First, get the specified number of unique nodes
        if node_type:
            node_query = f"""
            MATCH (n:{node_type})
            RETURN n
            ORDER BY CASE WHEN 'Document' IN labels(n) THEN 0 ELSE 1 END
            LIMIT {limit}
            """
        else:
            node_query = f"""
            MATCH (n)
            RETURN n
            ORDER BY CASE WHEN 'Document' IN labels(n) THEN 0 ELSE 1 END
            LIMIT {limit}
            """
        
        node_results = neo4j_client.execute_query(node_query)
        
        # Collect node info and build nodes_dict
        nodes_dict: Dict[str, Dict[str, Any]] = {}
        node_id_set: set = set()
        node_element_ids: set = set()
        
        for record in node_results:
            if "n" in record and record["n"]:
                node = record["n"]
                node_props = dict(node) if isinstance(node, dict) else node
                node_props = neo4j_client._convert_neo4j_types(node_props)
                labels = list(node.labels) if hasattr(node, "labels") else []
                
                if not labels:
                    # GraphRAG pipeline 创建的新类型
                    if node_props.get("filename") or node_props.get("kind") in ["pdf", "docx", "md"]:
                        labels = ["Document"]
                    elif node_props.get("type") == "chunk" or (node_props.get("chunk_id") is not None):
                        labels = ["Chunk"]
                    elif node_props.get("type") == "concept":
                        labels = ["Concept"]
                    elif node_props.get("type") == "entity":
                        labels = ["Entity"]
                    # GraphRAG 新增类型
                    elif node_props.get("summary") and node_props.get("keywords"):
                        labels = ["Theme"]
                    elif node_props.get("text") and node_props.get("confidence") is not None:
                        labels = ["Claim"]
                    else:
                        labels = ["Concept"]
                
                node_id = node_props.get("id") or node_props.get("name")
                if not node_id:
                    node_id = getattr(node, "element_id", None) or str(id(node))
                
                node_id = str(node_id)
                node_id_set.add(node_id)
                
                # Also collect Neo4j internal element_id for edge query
                element_id = getattr(node, "element_id", None)
                if element_id:
                    node_element_ids.add(element_id)
                
                nodes_dict[node_id] = {
                    "id": node_id,
                    "labels": labels,
                    "type": labels[0] if labels else "Unknown",
                    "label": node_props.get("label") or node_props.get("name") or node_props.get("filename") or (node_props.get("summary", "")[:30] if node_props.get("summary") else node_id),
                    "properties": node_props,
                    "degree": 0
                }
        
        edges: List[Dict[str, Any]] = []
        edge_id_set: set = set()
        
        # Get edges where both source and target are in our selected nodes
        if node_id_set:
            # Use element_id for more reliable edge matching
            if node_element_ids:
                edge_query = f"""
                MATCH (n)-[r]->(m)
                WHERE elementId(n) IN $element_ids AND elementId(m) IN $element_ids
                RETURN n, r, m
                LIMIT {edge_limit}
                """
                edge_results = neo4j_client.execute_query(edge_query, {"element_ids": list(node_element_ids)})
            else:
                # Fallback to property-based matching
                edge_query = f"""
                MATCH (n)-[r]->(m)
                WHERE (n.id IN $node_ids OR n.name IN $node_ids) AND (m.id IN $node_ids OR m.name IN $node_ids)
                RETURN n, r, m
                LIMIT {edge_limit}
                """
                edge_results = neo4j_client.execute_query(edge_query, {"node_ids": list(node_id_set)})
            
            for record in edge_results:
                if "r" in record and record["r"]:
                    rel = record["r"]
                    source_node = record.get("n")
                    target_node = record.get("m")
                    
                    if source_node and target_node:
                        source_props = dict(source_node) if isinstance(source_node, dict) else source_node
                        source_id = source_props.get("id") or source_props.get("name")
                        if not source_id:
                            source_id = getattr(source_node, "element_id", None) or str(id(source_node))
                        source_id = str(source_id)
                        
                        target_props = dict(target_node) if isinstance(target_node, dict) else target_node
                        target_id = target_props.get("id") or target_props.get("name")
                        if not target_id:
                            target_id = getattr(target_node, "element_id", None) or str(id(target_node))
                        target_id = str(target_id)
                        
                        # Only add edges where both endpoints are in our selected nodes
                        if source_id in node_id_set and target_id in node_id_set:
                            rel_type = rel.type if hasattr(rel, "type") else "RELATES_TO"
                            edge_unique_id = f"{source_id}_{rel_type}_{target_id}"
                            
                            # Avoid duplicate edges
                            if edge_unique_id not in edge_id_set:
                                edge_id_set.add(edge_unique_id)
                                rel_props = dict(rel) if isinstance(rel, dict) else rel
                                rel_props = neo4j_client._convert_neo4j_types(rel_props)
                                
                                edges.append({
                                    "id": edge_unique_id,
                                    "source": source_id,
                                    "target": target_id,
                                    "type": rel_type,
                                    "label": rel_type,
                                    "properties": rel_props
                                })
                                
                                if source_id in nodes_dict:
                                    nodes_dict[source_id]["degree"] += 1
                                if target_id in nodes_dict:
                                    nodes_dict[target_id]["degree"] += 1
        
        # Prepare response
        nodes = list(nodes_dict.values())
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "types": list(set(n.get("type", "Unknown") for n in nodes))
            }
        }
        
    except Exception as e:
        import traceback
        print(f"Error in visualize_graph: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to load graph data: {str(e)}")


@router.get("/query", response_model=GraphResponse)
async def query_graph(
    cypher: Optional[str] = Query(None, description="Cypher query"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Query the graph using Cypher.
    
    Example queries:
    - MATCH (n) RETURN n LIMIT 10
    - MATCH (c:Concept) RETURN c LIMIT 20
    - MATCH (d:Document)-[:MENTIONS]->(c:Concept) RETURN d, c LIMIT 10
    """
    if not cypher:
        # Default: get all nodes and relationships
        cypher = f"""
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT {limit}
        """
    
    try:
        results = neo4j_client.execute_query(cypher)
        
        nodes_dict = {}
        edges = []
        
        for record in results:
            # Extract nodes
            if "n" in record and record["n"]:
                node = record["n"]
                # Neo4j Node object: use dict(node) to get properties
                props = dict(node) if hasattr(node, "__getitem__") else {}
                labels = list(node.labels) if hasattr(node, "labels") else []
                
                # Get business ID from properties (id field in Document/Concept)
                # Fallback to name, or use Neo4j internal element_id
                node_id = props.get("id") or props.get("name")
                if not node_id:
                    # Use Neo4j internal ID as fallback
                    node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
                
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = Node(
                        id=str(node_id),
                        labels=labels,
                        properties=neo4j_client._convert_neo4j_types(props)
                    )
            
            if "m" in record and record["m"]:
                node = record["m"]
                props = dict(node) if hasattr(node, "__getitem__") else {}
                labels = list(node.labels) if hasattr(node, "labels") else []
                
                node_id = props.get("id") or props.get("name")
                if not node_id:
                    node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
                
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = Node(
                        id=str(node_id),
                        labels=labels,
                        properties=neo4j_client._convert_neo4j_types(props)
                    )
            
            # Extract relationships
            if "r" in record and record["r"]:
                rel = record["r"]
                source_node = record.get("n")
                target_node = record.get("m")
                
                if source_node and target_node:
                    # Get source ID (from properties first, fallback to element_id)
                    source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
                    source_id = source_props.get("id") or source_props.get("name")
                    if not source_id:
                        source_id = getattr(source_node, "element_id", None) or str(getattr(source_node, "id", hash(str(source_node))))
                    
                    # Get target ID
                    target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
                    target_id = target_props.get("id") or target_props.get("name")
                    if not target_id:
                        target_id = getattr(target_node, "element_id", None) or str(getattr(target_node, "id", hash(str(target_node))))
                    
                    if source_id and target_id:
                        rel_type = rel.type if hasattr(rel, "type") else str(rel)
                        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
                        
                        edges.append(Edge(
                            source=str(source_id),
                            target=str(target_id),
                            type=rel_type,
                            properties=neo4j_client._convert_neo4j_types(rel_props)
                        ))
        
        # Create response with cleaned properties
        response_nodes = [
            Node(id=node.id, labels=node.labels, properties=_clean_properties(node.properties))
            for node in nodes_dict.values()
        ]
        
        response_edges = [
            Edge(id=edge.id, source=edge.source, target=edge.target, type=edge.type,
                 properties=_clean_properties(edge.properties))
            for edge in edges
        ]
        
        return GraphResponse(
            nodes=response_nodes,
            edges=response_edges,
            stats={"count": len(results)}
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query error: {str(e)}")


@router.get("/nodes", response_model=List[Node])
async def get_nodes(
    label: Optional[str] = Query(None, description="Filter by label"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all nodes, optionally filtered by label."""
    if label:
        query = f"MATCH (n:{label}) RETURN n LIMIT $limit"
    else:
        query = "MATCH (n) RETURN n LIMIT $limit"
    
    results = neo4j_client.execute_query(query, {"limit": limit})
    
    nodes = []
    for record in results:
        node = record["n"]
        # Extract properties - execute_query should have already converted types
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        node_id = props.get("id") or props.get("name")
        if not node_id:
            node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
        
        # Double-convert to ensure all nested types are handled
        clean_props = neo4j_client._convert_neo4j_types(props)
        
        nodes.append(Node(
            id=str(node_id),
            labels=labels,
            properties=clean_props
        ))
    
    return nodes


@router.get("/edges", response_model=List[Edge])
async def get_edges(
    rel_type: Optional[str] = Query(None, description="Filter by relationship type"),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get all relationships, optionally filtered by type."""
    if rel_type:
        query = f"MATCH (a)-[r:{rel_type}]->(b) RETURN a, r, b LIMIT $limit"
    else:
        query = "MATCH (a)-[r]->(b) RETURN a, r, b LIMIT $limit"
    
    results = neo4j_client.execute_query(query, {"limit": limit})
    
    edges = []
    for record in results:
        source_node = record["a"]
        target_node = record["b"]
        rel = record["r"]
        
        # Get source ID
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        source_id = source_props.get("id") or source_props.get("name")
        if not source_id:
            source_id = getattr(source_node, "element_id", None) or str(getattr(source_node, "id", hash(str(source_node))))
        
        # Get target ID
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        target_id = target_props.get("id") or target_props.get("name")
        if not target_id:
            target_id = getattr(target_node, "element_id", None) or str(getattr(target_node, "id", hash(str(target_node))))
        
        if source_id and target_id:
            rel_type_str = rel.type if hasattr(rel, "type") else str(rel)
            rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
            
            # Double-convert to ensure all nested types are handled
            clean_rel_props = neo4j_client._convert_neo4j_types(rel_props)
            
            edges.append(Edge(
                source=str(source_id),
                target=str(target_id),
                type=rel_type_str,
                properties=clean_rel_props
            ))
    
    return edges


@router.get("/documents/{document_id}/graph", response_model=GraphResponse)
async def get_document_graph(
    document_id: str,
    depth: int = Query(2, ge=1, le=5, description="Relationship depth"),
    limit: int = Query(500, ge=10, le=10000, description="Maximum nodes to return"),
    edge_limit: int = Query(1000, ge=10, le=50000, description="Maximum edges to return")
):
    """
    获取指定文档的知识图谱。
    
    Args:
        document_id: 文档 ID
        depth: 关系深度（1-5）
        limit: 最大返回节点数
        edge_limit: 最大返回边数
        
    Returns:
        包含节点和边的图谱数据
    """
    # Check if document exists
    doc_check = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d",
        {"doc_id": document_id}
    )
    
    if not doc_check:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 获取文档节点及其关联节点（排除其他Document节点）
    node_query = f"""
    MATCH (d:Document {{id: $doc_id}})
    OPTIONAL MATCH (d)-[*1..{depth}]-(n)
    WHERE NOT (n:Document) OR n.id = $doc_id
    WITH d, COLLECT(DISTINCT n) AS related_nodes
    UNWIND related_nodes AS rn
    RETURN rn AS n
    UNION ALL
    MATCH (d:Document {{id: $doc_id}})
    RETURN d AS n
    ORDER BY CASE WHEN n.id = $doc_id THEN 0 ELSE 1 END
    LIMIT {limit}
    """
    
    node_results = neo4j_client.execute_query(node_query, {"doc_id": document_id})
    
    # Collect node info and build nodes_dict
    nodes_dict: Dict[str, Dict[str, Any]] = {}
    node_id_set: set = set()
    node_element_ids: set = set()
    
    for record in node_results:
        if "n" in record and record["n"]:
            node = record["n"]
            node_props = dict(node) if isinstance(node, dict) else node
            node_props = neo4j_client._convert_neo4j_types(node_props)
            
            # 关键修复：优先从 _labels 读取Neo4j原始标签
            # neo4j_client._convert_neo4j_types 已经将 Node.labels 存储在 _labels 中
            labels = node_props.pop('_labels', None) or []
            if isinstance(labels, str):
                labels = [labels]
            
            # 如果仍然没有labels，尝试从原始node对象获取（兼容旧代码）
            if not labels and hasattr(node, "labels"):
                labels = list(node.labels)
            
            # 如果仍然没有labels，通过属性推断类型
            if not labels:
                # GraphRAG pipeline 创建的新类型
                if node_props.get("filename") or node_props.get("kind") in ["pdf", "docx", "md"]:
                    labels = ["Document"]
                elif node_props.get("type") == "chunk" or (node_props.get("chunk_id") is not None):
                    labels = ["Chunk"]
                elif node_props.get("type") == "concept":
                    labels = ["Concept"]
                elif node_props.get("type") == "entity":
                    labels = ["Entity"]
                # GraphRAG 新增类型
                elif node_props.get("summary") and node_props.get("keywords"):
                    labels = ["Theme"]
                elif node_props.get("text") and node_props.get("confidence") is not None:
                    labels = ["Claim"]
                else:
                    labels = ["Concept"]
            
            node_id = node_props.get("id") or node_props.get("name")
            if not node_id:
                node_id = getattr(node, "element_id", None) or str(id(node))
            
            node_id = str(node_id)
            node_id_set.add(node_id)
            
            # Also collect Neo4j internal element_id for edge query
            element_id = getattr(node, "element_id", None)
            if element_id:
                node_element_ids.add(element_id)
            
            nodes_dict[node_id] = {
                "id": node_id,
                "labels": labels,
                "type": labels[0] if labels else "Unknown",
                "label": node_props.get("name") or node_props.get("filename") or node_id,
                "properties": node_props,
                "degree": 0
            }
    
    edges: List[Dict[str, Any]] = []
    edge_id_set: set = set()
    
    # Get edges - query all edges between nodes in node_id_set
    if node_id_set:
        node_id_list = list(node_id_set)
        
        # 使用更简单直接的边查询：先找到Document，然后获取它和所有相关节点之间的边
        edge_query = f"""
        MATCH (d:Document {{id: $doc_id}})
        OPTIONAL MATCH (d)-[*1..{depth}]-(n)
        WHERE NOT (n:Document) OR n.id = $doc_id
        WITH d, COLLECT(DISTINCT n) AS related_nodes
        WITH [d] + related_nodes AS all_nodes
        UNWIND all_nodes AS source
        WITH source, all_nodes
        MATCH (source)-[r]->(target)
        WHERE target IN all_nodes AND source <> target
        RETURN DISTINCT source AS n, r, target AS m
        LIMIT {edge_limit}
        """
        edge_results = neo4j_client.execute_query(edge_query, {"doc_id": document_id})
        
        for record in edge_results:
            if "r" in record and record["r"]:
                rel = record["r"]
                source_node = record.get("n")
                target_node = record.get("m")
                
                if source_node and target_node:
                    source_props = dict(source_node) if isinstance(source_node, dict) else source_node
                    source_props = neo4j_client._convert_neo4j_types(source_props)
                    source_id = source_props.get("id") or source_props.get("name")
                    if not source_id:
                        source_id = getattr(source_node, "element_id", None) or str(id(source_node))
                    source_id = str(source_id)
                    
                    target_props = dict(target_node) if isinstance(target_node, dict) else target_node
                    target_props = neo4j_client._convert_neo4j_types(target_props)
                    target_id = target_props.get("id") or target_props.get("name")
                    if not target_id:
                        target_id = getattr(target_node, "element_id", None) or str(id(target_node))
                    target_id = str(target_id)
                    
                    rel_type = rel.type if hasattr(rel, "type") else "RELATES_TO"
                    
                    # Only add edges where both endpoints are in our selected nodes
                    if source_id in node_id_set and target_id in node_id_set:
                        edge_unique_id = f"{source_id}_{rel_type}_{target_id}"
                        
                        # Avoid duplicate edges
                        if edge_unique_id not in edge_id_set:
                            edge_id_set.add(edge_unique_id)
                            rel_props = dict(rel) if isinstance(rel, dict) else rel
                            rel_props = neo4j_client._convert_neo4j_types(rel_props)
                            
                            edges.append({
                                "id": edge_unique_id,
                                "source": source_id,
                                "target": target_id,
                                "type": rel_type,
                                "label": rel_type,
                                "properties": rel_props
                            })
                            
                            # Update degree counts
                            if source_id in nodes_dict:
                                nodes_dict[source_id]["degree"] += 1
                            if target_id in nodes_dict:
                                nodes_dict[target_id]["degree"] += 1

    try:
        neo4j_client.mark_document_processed(document_id, "completed")
    except Exception:
        # best-effort，不阻塞图谱返回
        pass
    
    # Prepare response - return raw dict format matching /graph/visualize endpoint
    response_nodes = list(nodes_dict.values())
    
    # Clean edge properties
    response_edges = []
    for edge in edges:
        response_edges.append({
            "id": edge["id"],
            "source": str(edge["source"]),
            "target": str(edge["target"]),
            "type": edge["type"],
            "label": edge["label"],
            "properties": _clean_properties(edge.get("properties", {}))
        })

    return {
        "nodes": response_nodes,
        "edges": response_edges,
        "stats": {"count": len(response_nodes), "edges": len(response_edges)}
    }


@router.get("/concepts/{concept_name}/graph", response_model=GraphResponse)
async def get_concept_graph(
    concept_name: str,
    depth: int = Query(2, ge=1, le=5, description="Relationship depth")
):
    """
    获取指定概念的知识图谱。
    
    Args:
        concept_name: 概念名称
        depth: 关系深度（1-5）
        
    Returns:
        包含节点和边的图谱数据
    """
    # Check if concept exists
    concept_check = neo4j_client.execute_query(
        "MATCH (c:Concept {name: $name}) RETURN c",
        {"name": concept_name}
    )
    
    if not concept_check:
        raise HTTPException(status_code=404, detail="Concept not found")
    
    # Query for concept and related nodes
    query = f"""
    MATCH (c:Concept {{name: $name}})
    MATCH path = (c)-[*1..{depth}]-(n)
    WITH c, n, relationships(path) as rels
    RETURN c, n, rels
    LIMIT 1000
    """
    
    results = neo4j_client.execute_query(query, {"name": concept_name})
    
    nodes_dict = {}
    edges = []
    
    for record in results:
        # Add central concept node
        if "c" in record and record["c"]:
            concept_node = record["c"]
            concept_props = dict(concept_node) if hasattr(concept_node, "__getitem__") else {}
            concept_labels = list(concept_node.labels) if hasattr(concept_node, "labels") else ["Concept"]
            
            concept_id = concept_props.get("name") or concept_props.get("id")
            if not concept_id:
                concept_id = getattr(concept_node, "element_id", None) or str(getattr(concept_node, "id", hash(str(concept_node))))
            
            if concept_id not in nodes_dict:
                nodes_dict[concept_id] = Node(
                    id=str(concept_id),
                    labels=concept_labels,
                    properties=concept_props
                )
        
        # Add related node
        if "n" in record and record["n"]:
            node = record["n"]
            props = dict(node) if hasattr(node, "__getitem__") else {}
            labels = list(node.labels) if hasattr(node, "labels") else []
            
            node_id = props.get("id") or props.get("name")
            if not node_id:
                node_id = getattr(node, "element_id", None) or str(getattr(node, "id", hash(str(node))))
            
            if node_id not in nodes_dict:
                nodes_dict[node_id] = {
                    "id": str(node_id),
                    "labels": labels,
                    "type": labels[0] if labels else "Unknown",
                    "label": props.get("name") or props.get("filename") or node_id,
                    "properties": neo4j_client._convert_neo4j_types(props),
                    "degree": 0
                }
        
        # Add relationships
        if "rels" in record and record["rels"]:
            for rel in record["rels"]:
                if hasattr(rel, "start_node") and hasattr(rel, "end_node"):
                    # Get source ID - use same logic as node ID generation
                    start_props = dict(rel.start_node) if hasattr(rel.start_node, "__getitem__") else {}
                    source_id = start_props.get("id") or start_props.get("name")
                    if not source_id:
                        source_id = getattr(rel.start_node, "element_id", None) or str(getattr(rel.start_node, "id", hash(str(rel.start_node))))
                    
                    # Get target ID - use same logic as node ID generation
                    end_props = dict(rel.end_node) if hasattr(rel.end_node, "__getitem__") else {}
                    target_id = end_props.get("id") or end_props.get("name")
                    if not target_id:
                        target_id = getattr(rel.end_node, "element_id", None) or str(getattr(rel.end_node, "id", hash(str(rel.end_node))))
                    
                    # Convert to string
                    source_id = str(source_id)
                    target_id = str(target_id)
                    
                    # 从nodes_dict中查找正确的节点ID（处理ID不匹配的情况）
                    final_source_id = source_id
                    final_target_id = target_id
                    
                    for node_id in nodes_dict:
                        node = nodes_dict[node_id]
                        node_props = node.get("properties", {})
                        # 匹配条件：节点属性中的id或name与source/target匹配
                        if (node_props.get("id") == source_id or 
                            node_props.get("name") == source_id or
                            str(node.get("id")) == source_id or
                            str(node.get("label")) == source_id):
                            final_source_id = node_id
                        if (node_props.get("id") == target_id or 
                            node_props.get("name") == target_id or
                            str(node.get("id")) == target_id or
                            str(node.get("label")) == target_id):
                            final_target_id = node_id
                    
                    rel_type = rel.type if hasattr(rel, "type") else "RELATES_TO"
                    rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
                    
                    edges.append({
                        "id": f"{final_source_id}_{rel_type}_{final_target_id}",
                        "source": final_source_id,
                        "target": final_target_id,
                        "type": rel_type,
                        "label": rel_type,
                        "properties": neo4j_client._convert_neo4j_types(rel_props)
                    })
    
    # Create response with cleaned properties
    response_nodes = [
        Node(id=node.id, labels=node.labels, properties=_clean_properties(node.properties))
        for node in nodes_dict.values()
    ]
    
    response_edges = [
        Edge(id=edge.id, source=edge.source, target=edge.target, type=edge.type,
             properties=_clean_properties(edge.properties))
        for edge in edges
    ]
    
    return GraphResponse(
        nodes=response_nodes,
        edges=response_edges,
        stats={"count": len(response_nodes), "edges": len(response_edges)}
    )


@router.get("/stats")
async def get_graph_stats():
    """Get knowledge graph statistics."""
    try:
        # 单独查询文档总数
        docs_query = "MATCH (d:Document) RETURN count(d) as totalDocuments"
        docs_result = neo4j_client.execute_query(docs_query)
        total_docs = docs_result[0]["totalDocuments"] if docs_result and len(docs_result) > 0 else 0

        # 单独查询概念总数
        concepts_query = "MATCH (c:Concept) RETURN count(c) as totalConcepts"
        concepts_result = neo4j_client.execute_query(concepts_query)
        total_concepts = concepts_result[0]["totalConcepts"] if concepts_result and len(concepts_result) > 0 else 0

        # 单独查询关系总数
        relations_query = "MATCH ()-[r]->() RETURN count(r) as totalRelations"
        relations_result = neo4j_client.execute_query(relations_query)
        total_relations = relations_result[0]["totalRelations"] if relations_result and len(relations_result) > 0 else 0

        # 获取最近文档
        recent_docs = []
        try:
            recent_docs_query = """
            MATCH (d:Document)
            RETURN d.id as id, d.filename as filename, d.created_at as createdAt, d.kind as kind
            ORDER BY d.created_at DESC
            LIMIT 5
            """
            recent_docs_result = neo4j_client.execute_query(recent_docs_query)
            recent_docs = [
                {
                    "id": doc.get("id", ""),
                    "filename": doc.get("filename", "未命名文档"),
                    "createdAt": doc.get("createdAt", ""),
                    "kind": doc.get("kind", "unknown")
                }
                for doc in recent_docs_result
            ] if recent_docs_result else []
        except Exception as docs_error:
            print(f"获取最近文档失败: {docs_error}")
            recent_docs = []

        # 获取顶级概念
        top_concepts = []
        try:
            top_concepts_query = """
            MATCH (c:Concept)
            OPTIONAL MATCH (c)-[r]-(other)
            WITH c, count(r) as connections
            RETURN c.name as name, c.domain as domain, connections
            ORDER BY connections DESC
            LIMIT 10
            """
            top_concepts_result = neo4j_client.execute_query(top_concepts_query)
            top_concepts = [
                {
                    "name": concept.get("name", "未知概念"),
                    "domain": concept.get("domain", ""),
                    "connections": concept.get("connections", 0)
                }
                for concept in top_concepts_result
            ] if top_concepts_result else []
        except Exception as concepts_error:
            print(f"获取顶级概念失败: {concepts_error}")
            top_concepts = []

        # 获取关系类型分布
        relation_types = []
        try:
            relation_types_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
            """
            relation_types_result = neo4j_client.execute_query(relation_types_query)
            relation_types = [
                {
                    "type": rt.get("type", "未知类型"),
                    "count": rt.get("count", 0)
                }
                for rt in relation_types_result
            ] if relation_types_result else []
        except Exception as relations_error:
            print(f"获取关系类型失败: {relations_error}")
            relation_types = []

        # 获取主题社区数
        community_count = 0
        try:
            community_query = """
            MATCH (t:Theme)
            RETURN count(DISTINCT t.community_id) as communityCount
            """
            community_result = neo4j_client.execute_query(community_query)
            community_count = community_result[0]["communityCount"] if community_result and len(community_result) > 0 else 0
        except Exception as community_error:
            print(f"获取主题社区数失败: {community_error}")
            community_count = 0

        result = {
            "totalDocuments": int(total_docs),
            "totalConcepts": int(total_concepts),
            "totalRelations": int(total_relations),
            "communityCount": community_count,
            "recentDocuments": recent_docs,
            "topConcepts": top_concepts,
            "relationTypes": relation_types
        }

        print(f"最终返回数据: {result}")  # 调试信息
        return result

    except Exception as e:
        # 返回默认空数据
        return {
            "totalDocuments": 0,
            "totalConcepts": 0,
            "totalRelations": 0,
            "communityCount": 0,
            "recentDocuments": [],
            "topConcepts": [],
            "relationTypes": []
        }

# @router.get("/stats")
# async def get_graph_stats():
#     """Get knowledge graph statistics."""
#     try:
#         # Get total counts
#         stats_query = """
#         MATCH (d:Document)
#         WITH count(d) as totalDocs
#         MATCH (c:Concept)
#         WITH totalDocs, count(c) as totalConcepts
#         MATCH ()-[r]->()
#         RETURN
#             totalDocs,
#             totalConcepts,
#             count(r) as totalRelations
#         """
#         stats_result = neo4j_client.execute_query(stats_query)
#
#         if not stats_result:
#             return {
#                 "totalDocuments": 0,
#                 "totalConcepts": 0,
#                 "totalRelations": 0,
#                 "recentDocuments": [],
#                 "topConcepts": [],
#                 "relationTypes": []
#             }
#
#         stats = stats_result[0]
#
#         # Get recent documents
#         recent_docs_query = """
#         MATCH (d:Document)
#         RETURN d.id as id, d.filename as filename, d.created_at as createdAt, d.kind as kind
#         ORDER BY d.created_at DESC
#         LIMIT 5
#         """
#         recent_docs = neo4j_client.execute_query(recent_docs_query)
#
#         # Get top concepts by connection count
#         top_concepts_query = """
#         MATCH (c:Concept)
#         OPTIONAL MATCH (c)-[r]-()
#         WITH c, count(r) as connections
#         RETURN c.name as name, c.domain as domain, connections
#         ORDER BY connections DESC
#         LIMIT 10
#         """
#         top_concepts = neo4j_client.execute_query(top_concepts_query)
#
#         # Get relation type distribution
#         relation_types_query = """
#         MATCH ()-[r]->()
#         RETURN type(r) as type, count(r) as count
#         ORDER BY count DESC
#         """
#         relation_types = neo4j_client.execute_query(relation_types_query)
#
#         return {
#             "totalDocuments": stats.get("totalDocs", 0),
#             "totalConcepts": stats.get("totalConcepts", 0),
#             "totalRelations": stats.get("totalRelations", 0),
#             "recentDocuments": [
#                 {
#                     "id": doc.get("id"),
#                     "filename": doc.get("filename"),
#                     "createdAt": doc.get("createdAt"),
#                     "kind": doc.get("kind")
#                 }
#                 for doc in recent_docs
#             ],
#             "topConcepts": [
#                 {
#                     "name": concept.get("name"),
#                     "domain": concept.get("domain"),
#                     "connections": concept.get("connections", 0)
#                 }
#                 for concept in top_concepts
#             ],
#             "relationTypes": [
#                 {
#                     "type": rt.get("type"),
#                     "count": rt.get("count", 0)
#                 }
#                 for rt in relation_types
#             ]
#         }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ========== Node CRUD Operations ==========

@router.post("/nodes", response_model=Node, status_code=201)
async def create_node(node_data: NodeCreate = Body(...)):
    """
    创建新节点。
    
    Args:
        node_data: 节点数据（标签和属性）
        
    Returns:
        创建的节点
    """
    try:
        import uuid
        from datetime import datetime
        
        # Generate unique ID if not provided
        if "id" not in node_data.properties:
            node_data.properties["id"] = str(uuid.uuid4())
        
        # Add creation timestamp
        if "created_at" not in node_data.properties:
            node_data.properties["created_at"] = datetime.now().isoformat()
        
        # Build labels string
        labels_str = ":".join(node_data.labels)
        
        # Build properties
        props_dict = node_data.properties
        
        # Create node
        query = f"""
        CREATE (n:{labels_str})
        SET n = $props
        RETURN n
        """
        
        results = neo4j_client.execute_query(query, {"props": props_dict})
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create node")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id")),
            labels=labels,
            properties=neo4j_client._convert_neo4j_types(props)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create node: {str(e)}")


@router.get("/nodes/{node_id}", response_model=Node)
async def get_node(node_id: str):
    """
    获取指定节点。
    
    Args:
        node_id: 节点 ID
        
    Returns:
        节点数据
    """
    try:
        # Try to find by id property first, then by name
        query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        
        results = neo4j_client.execute_query(query, {"node_id": node_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id") or props.get("name") or node_id),
            labels=labels,
            properties=neo4j_client._convert_neo4j_types(props)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")


@router.put("/nodes/{node_id}", response_model=Node)
async def update_node(node_id: str, node_data: NodeUpdate = Body(...)):
    """
    更新节点。
    
    Args:
        node_id: 节点 ID
        node_data: 更新数据
        
    Returns:
        更新后的节点
    """
    try:
        from datetime import datetime
        
        # Check if node exists
        check_query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {"node_id": node_id})
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Build update query
        updates = []
        params = {"node_id": node_id}
        
        # Update labels if provided
        if node_data.labels:
            labels_str = ":".join(node_data.labels)
            # Remove old labels and set new ones
            query_parts = [
                f"""
                MATCH (n)
                WHERE n.id = $node_id OR n.name = $node_id
                REMOVE n:{":".join(list(check_results[0]["n"].labels))}
                SET n:{labels_str}
                """
            ]
        else:
            query_parts = [
                """
                MATCH (n)
                WHERE n.id = $node_id OR n.name = $node_id
                """
            ]
        
        # Update properties
        if node_data.properties:
            node_data.properties["updated_at"] = datetime.now().isoformat()
            params["props"] = node_data.properties
            query_parts.append("SET n += $props")
        
        # Remove properties
        if node_data.remove_properties:
            for prop in node_data.remove_properties:
                query_parts.append(f"REMOVE n.{prop}")
        
        query_parts.append("RETURN n")
        query = "\n".join(query_parts)
        
        results = neo4j_client.execute_query(query, params)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to update node")
        
        node = results[0]["n"]
        props = dict(node) if hasattr(node, "__getitem__") else {}
        labels = list(node.labels) if hasattr(node, "labels") else []
        
        return Node(
            id=str(props.get("id") or props.get("name") or node_id),
            labels=labels,
            properties=neo4j_client._convert_neo4j_types(props)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update node: {str(e)}")


@router.delete("/nodes/{node_id}", status_code=204)
async def delete_node(node_id: str, force: bool = Query(False, description="Force delete with relationships")):
    """
    删除节点。
    
    Args:
        node_id: 节点 ID
        force: 是否强制删除（包括关系）
        
    Returns:
        无内容
    """
    try:
        # Check if node exists
        check_query = """
        MATCH (n)
        WHERE n.id = $node_id OR n.name = $node_id
        RETURN n
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {"node_id": node_id})
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Check for relationships if not force delete
        if not force:
            rel_check_query = """
            MATCH (n)-[r]-()
            WHERE n.id = $node_id OR n.name = $node_id
            RETURN count(r) as rel_count
            """
            rel_results = neo4j_client.execute_query(rel_check_query, {"node_id": node_id})
            
            if rel_results and rel_results[0].get("rel_count", 0) > 0:
                raise HTTPException(
                    status_code=400,
                    detail="Node has relationships. Use force=true to delete with relationships."
                )
        
        # Delete node (and relationships if force)
        if force:
            delete_query = """
            MATCH (n)
            WHERE n.id = $node_id OR n.name = $node_id
            DETACH DELETE n
            """
        else:
            delete_query = """
            MATCH (n)
            WHERE n.id = $node_id OR n.name = $node_id
            DELETE n
            """
        
        neo4j_client.execute_query(delete_query, {"node_id": node_id})
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete node: {str(e)}")


# ========== Edge (Relationship) CRUD Operations ==========

@router.post("/edges", response_model=Edge, status_code=201)
async def create_edge(edge_data: EdgeCreate = Body(...)):
    """
    创建新关系。
    
    Args:
        edge_data: 关系数据
        
    Returns:
        创建的关系
    """
    try:
        from datetime import datetime
        
        # Check if source and target nodes exist
        check_query = """
        MATCH (s)
        WHERE s.id = $source_id OR s.name = $source_id
        MATCH (t)
        WHERE t.id = $target_id OR t.name = $target_id
        RETURN s, t
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": edge_data.source,
            "target_id": edge_data.target
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Source or target node not found")
        
        # Add creation timestamp
        props = edge_data.properties.copy()
        if "created_at" not in props:
            props["created_at"] = datetime.now().isoformat()
        
        # Create relationship
        query = f"""
        MATCH (s)
        WHERE s.id = $source_id OR s.name = $source_id
        MATCH (t)
        WHERE t.id = $target_id OR t.name = $target_id
        CREATE (s)-[r:{edge_data.type}]->(t)
        SET r = $props
        RETURN s, r, t
        """
        
        results = neo4j_client.execute_query(query, {
            "source_id": edge_data.source,
            "target_id": edge_data.target,
            "props": props
        })
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to create relationship")
        
        rel = results[0]["r"]
        source_node = results[0]["s"]
        target_node = results[0]["t"]
        
        # Get IDs
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        source_id = source_props.get("id") or source_props.get("name") or edge_data.source
        
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        target_id = target_props.get("id") or target_props.get("name") or edge_data.target
        
        rel_type = rel.type if hasattr(rel, "type") else edge_data.type
        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
        
        # Generate edge ID
        edge_id = f"{source_id}-{rel_type}-{target_id}"
        
        return Edge(
            id=edge_id,
            source=str(source_id),
            target=str(target_id),
            type=rel_type,
            properties=neo4j_client._convert_neo4j_types(rel_props)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create relationship: {str(e)}")


@router.put("/edges/{source_id}/{target_id}/{rel_type}", response_model=Edge)
async def update_edge(
    source_id: str,
    target_id: str,
    rel_type: str,
    edge_data: EdgeUpdate = Body(...)
):
    """
    更新关系。
    
    Args:
        source_id: 源节点 ID
        target_id: 目标节点 ID
        rel_type: 关系类型
        edge_data: 更新数据
        
    Returns:
        更新后的关系
    """
    try:
        from datetime import datetime
        
        # Check if relationship exists
        check_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        RETURN r
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        # Update properties
        updates = []
        params = {
            "source_id": source_id,
            "target_id": target_id
        }
        
        if edge_data.properties:
            edge_data.properties["updated_at"] = datetime.now().isoformat()
            params["props"] = edge_data.properties
            updates.append("SET r += $props")
        
        # Remove properties
        if edge_data.remove_properties:
            for prop in edge_data.remove_properties:
                updates.append(f"REMOVE r.{prop}")
        
        # Handle type change (requires recreating the relationship)
        if edge_data.type and edge_data.type != rel_type:
            query = f"""
            MATCH (s)-[r:{rel_type}]->(t)
            WHERE (s.id = $source_id OR s.name = $source_id)
              AND (t.id = $target_id OR t.name = $target_id)
            WITH s, t, properties(r) as props
            DELETE r
            CREATE (s)-[new_r:{edge_data.type}]->(t)
            SET new_r = props
            {" ".join(updates).replace("r.", "new_r.").replace("r +=", "new_r +=")}
            RETURN s, new_r as r, t
            """
        else:
            query = f"""
            MATCH (s)-[r:{rel_type}]->(t)
            WHERE (s.id = $source_id OR s.name = $source_id)
              AND (t.id = $target_id OR t.name = $target_id)
            {" ".join(updates)}
            RETURN s, r, t
            """
        
        results = neo4j_client.execute_query(query, params)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to update relationship")
        
        rel = results[0]["r"]
        source_node = results[0]["s"]
        target_node = results[0]["t"]
        
        # Get IDs
        source_props = dict(source_node) if hasattr(source_node, "__getitem__") else {}
        actual_source_id = source_props.get("id") or source_props.get("name") or source_id
        
        target_props = dict(target_node) if hasattr(target_node, "__getitem__") else {}
        actual_target_id = target_props.get("id") or target_props.get("name") or target_id
        
        rel_type_actual = rel.type if hasattr(rel, "type") else (edge_data.type or rel_type)
        rel_props = dict(rel) if hasattr(rel, "__getitem__") else {}
        
        edge_id = f"{actual_source_id}-{rel_type_actual}-{actual_target_id}"
        
        return Edge(
            id=edge_id,
            source=str(actual_source_id),
            target=str(actual_target_id),
            type=rel_type_actual,
            properties=neo4j_client._convert_neo4j_types(rel_props)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update relationship: {str(e)}")


@router.delete("/edges/{source_id}/{target_id}/{rel_type}", status_code=204)
async def delete_edge(source_id: str, target_id: str, rel_type: str):
    """
    删除关系。
    
    Args:
        source_id: 源节点 ID
        target_id: 目标节点 ID
        rel_type: 关系类型
        
    Returns:
        无内容
    """
    try:
        # Check if relationship exists
        check_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        RETURN r
        LIMIT 1
        """
        check_results = neo4j_client.execute_query(check_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not check_results:
            raise HTTPException(status_code=404, detail="Relationship not found")
        
        # Delete relationship
        delete_query = f"""
        MATCH (s)-[r:{rel_type}]->(t)
        WHERE (s.id = $source_id OR s.name = $source_id)
          AND (t.id = $target_id OR t.name = $target_id)
        DELETE r
        """
        
        neo4j_client.execute_query(delete_query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete relationship: {str(e)}")


# ========== Bulk Delete Operations ==========

@router.delete("/purge/all")
async def purge_all_graph(
    confirm: bool = Query(False, description="Confirm deletion (must be true)"),
    safety_check: str = Query(None, description="Safety check: must be 'YES_I_AM_SURE'")
):
    """
    清空整个知识图谱（危险操作！）
    
    删除所有节点和关系，包括 Document、Concept、Topic 等。
    
    Args:
        confirm: 必须设置为 true
        safety_check: 必须设置为 'YES_I_AM_SURE'
    
    Returns:
        删除统计信息
    """
    if not confirm or safety_check != "YES_I_AM_SURE":
        raise HTTPException(
            status_code=400,
            detail="请确认删除操作：需要设置 confirm=true 和 safety_check='YES_I_AM_SURE'"
        )
    
    try:
        result = neo4j_client.delete_all_graph_data()
        return {
            "message": "知识图谱已完全清空",
            "deleted_nodes": result["deleted_nodes"],
            "deleted_relationships": result["deleted_relationships"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/purge/concepts")
async def purge_all_concepts(
    confirm: bool = Query(False, description="Confirm deletion (must be true)")
):
    """
    清空所有概念节点（Concept）
    
    删除所有 Concept 节点及其相关关系。
    
    Args:
        confirm: 必须设置为 true
    
    Returns:
        删除统计信息
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="请确认删除操作：需要设置 confirm=true"
        )
    
    try:
        result = neo4j_client.delete_all_concepts()
        return {
            "message": "所有概念节点已删除",
            "deleted_concepts": result["deleted_concepts"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/purge/documents")
async def purge_all_documents(
    confirm: bool = Query(False, description="Confirm deletion (must be true)")
):
    """
    清空所有文档节点（Document）
    
    删除所有 Document 节点及其相关关系。
    
    Args:
        confirm: 必须设置为 true
    
    Returns:
        删除统计信息
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="请确认删除操作：需要设置 confirm=true"
        )
    
    try:
        result = neo4j_client.delete_all_documents()
        return {
            "message": "所有文档节点已删除",
            "deleted_documents": result["deleted_documents"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
