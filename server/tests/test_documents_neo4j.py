#!/usr/bin/env python3
"""
Quick verification script for Documents API
测试后端文档管理 API
"""

import sys
sys.path.insert(0, '..')

from infra.neo4j_client import Neo4jClient

def test_documents_api():
    """Test documents listing and detail APIs"""
    
    client = Neo4jClient()
    client.initialize()
    print("✓ Neo4j 连接成功\n")
    
    # Test 1: Get total document count
    print("=" * 60)
    print("测试 1: 获取文档总数")
    print("=" * 60)
    total_result = client.execute_query("MATCH (d:Document) RETURN count(d) as total")
    total = total_result[0]["total"] if total_result else 0
    print(f"✓ 文档总数: {total}\n")
    
    # Test 2: List documents
    print("=" * 60)
    print("测试 2: 列出所有文档")
    print("=" * 60)
    query = """
    MATCH (d:Document)
    OPTIONAL MATCH (d)<-[:CHUNK_OF]-(chunk:Chunk)
    OPTIONAL MATCH (d)<-[:BELONGS_TO]-(concept:Concept)
    OPTIONAL MATCH (d)<-[:BELONGS_TO]-(claim:Claim)
    RETURN DISTINCT
        d.id AS id,
        d.filename AS filename,
        d.kind AS kind,
        d.size AS size,
        d.created_at AS created_at,
        count(DISTINCT chunk) AS chunk_count,
        count(DISTINCT concept) AS concept_count,
        count(DISTINCT claim) AS claim_count
    LIMIT 5
    """
    
    results = client.execute_query(query)
    if results:
        print(f"✓ 获取到 {len(results)} 条文档记录\n")
        for i, doc in enumerate(results, 1):
            print(f"  [{i}] {doc.get('filename', 'N/A')}")
            print(f"      - ID: {doc.get('id', 'N/A')}")
            print(f"      - 类型: {doc.get('kind', 'N/A')}")
            print(f"      - 大小: {doc.get('size', 'N/A')} 字节")
            print(f"      - 文本块: {doc.get('chunk_count', 0)}")
            print(f"      - 概念: {doc.get('concept_count', 0)}")
            print(f"      - 论断: {doc.get('claim_count', 0)}")
            print()
    else:
        print("⚠ 未找到任何文档\n")
    
    # Test 3: Get document detail (if any document exists)
    if results:
        print("=" * 60)
        print("测试 3: 获取文档详细信息")
        print("=" * 60)
        doc_id = results[0]["id"]
        
        # Get basic info
        doc_result = client.execute_query(
            "MATCH (d:Document {id: $doc_id}) RETURN d",
            {"doc_id": doc_id}
        )
        
        if doc_result:
            doc_data = doc_result[0]["d"]
            print(f"✓ 文档 {doc_id} 的基本信息:")
            print(f"  - 文件名: {doc_data.get('filename', 'N/A')}")
            print(f"  - MIME: {doc_data.get('mime', 'N/A')}")
            print(f"  - 创建时间: {doc_data.get('created_at', 'N/A')}\n")
            
            # Get statistics
            stats_query = """
            MATCH (d:Document {id: $doc_id})
            OPTIONAL MATCH (d)<-[:CHUNK_OF]-(chunk:Chunk)
            OPTIONAL MATCH (chunk)-[:MENTIONS]-(concept:Concept)
            OPTIONAL MATCH (chunk)-[:MENTIONS]-(claim:Claim)
            OPTIONAL MATCH (concept)-[r]-(other)
            RETURN
                count(DISTINCT chunk) AS chunk_count,
                count(DISTINCT concept) AS concept_count,
                count(DISTINCT claim) AS claim_count,
                count(DISTINCT r) AS relation_count
            """
            
            stats_result = client.execute_query(stats_query, {"doc_id": doc_id})
            if stats_result:
                stats = stats_result[0]
                print(f"✓ 处理统计:")
                print(f"  - 文本块: {stats.get('chunk_count', 0)}")
                print(f"  - 概念: {stats.get('concept_count', 0)}")
                print(f"  - 论断: {stats.get('claim_count', 0)}")
                print(f"  - 关系: {stats.get('relation_count', 0)}\n")
            
            # Get associated themes
            themes_query = """
            MATCH (d:Document {id: $doc_id})<-[:BELONGS_TO]-(c:Concept)-[:BELONGS_TO_THEME]->(t:Theme)
            RETURN DISTINCT
                t.id AS id,
                t.label AS label,
                t.level AS level,
                t.member_count AS member_count
            LIMIT 5
            """
            
            themes_result = client.execute_query(themes_query, {"doc_id": doc_id})
            if themes_result:
                print(f"✓ 关联主题 ({len(themes_result)} 个):")
                for theme in themes_result:
                    print(f"  - {theme.get('label', 'N/A')} (Level {theme.get('level', 'N/A')}, {theme.get('member_count', 0)} 成员)")
            else:
                print("⚠ 未找到关联主题\n")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_documents_api()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
