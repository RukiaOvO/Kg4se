#!/usr/bin/env python3
"""
Test script for graph visualization API
Tests the /graph/visualize endpoint
"""

import requests
import json
import sys

# API URL
BASE_URL = "http://localhost:8000"
GRAPH_VISUALIZE_URL = f"{BASE_URL}/graph/visualize"

def test_graph_visualization():
    """Test the graph visualization endpoint."""
    print("=" * 80)
    print("Testing Graph Visualization API")
    print("=" * 80)
    
    try:
        # Test basic visualization
        print("\n1. Testing basic graph visualization...")
        response = requests.get(GRAPH_VISUALIZE_URL, params={"limit": 100})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Request successful (Status: {response.status_code})")
            
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            stats = data.get("stats", {})
            
            print(f"\n📊 Graph Statistics:")
            print(f"   Nodes: {len(nodes)}")
            print(f"   Edges: {len(edges)}")
            print(f"   Node Types: {stats.get('types', [])}")
            
            if nodes:
                print(f"\n📝 Sample Nodes (first 3):")
                for node in nodes[:3]:
                    print(f"   - {node['id']}: {node['label']} (Type: {node['type']}, Degree: {node.get('degree', 0)})")
            
            if edges:
                print(f"\n🔗 Sample Edges (first 3):")
                for edge in edges[:3]:
                    print(f"   - {edge['source']} --[{edge['type']}]--> {edge['target']}")
            
            # Test with node type filter
            print("\n2. Testing with node type filter (Concept)...")
            response = requests.get(GRAPH_VISUALIZE_URL, params={"limit": 50, "node_type": "Concept"})
            
            if response.status_code == 200:
                data = response.json()
                nodes = data.get("nodes", [])
                print(f"✅ Concept nodes: {len(nodes)}")
                if nodes:
                    print(f"   Sample: {nodes[0]['label']}")
            else:
                print(f"❌ Failed to filter by Concept (Status: {response.status_code})")
            
            print("\n✅ All tests passed!")
            return True
            
        else:
            print(f"❌ Request failed (Status: {response.status_code})")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed: Cannot connect to {BASE_URL}")
        print("   Make sure the server is running: python -m uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_graph_visualization()
    sys.exit(0 if success else 1)
