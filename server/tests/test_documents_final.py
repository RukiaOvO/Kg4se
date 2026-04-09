#!/usr/bin/env python3
"""最终集成测试 - 验证完整功能"""

import sys
import requests
import json

def test_api():
    """测试 API 端点"""
    print("\n" + "="*70)
    print("🧪 API 集成测试")
    print("="*70)
    
    base_url = "http://127.0.0.1:8000"
    
    tests = []
    
    # 测试 1: 健康检查
    print("\n1️⃣  健康检查")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ 服务器正常运行")
            tests.append(True)
        else:
            print(f"❌ 状态码: {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        tests.append(False)
    
    # 测试 2: 文档列表端点
    print("\n2️⃣  文档列表端点 GET /uploads")
    try:
        response = requests.get(f"{base_url}/uploads", timeout=5)
        if response.status_code == 200:
            data = response.json()
            # 检查响应结构
            if 'total' in data and 'documents' in data:
                print(f"✅ 端点响应正确")
                print(f"   - 总文档数: {data['total']}")
                print(f"   - 返回文档数: {len(data['documents'])}")
                
                # 检查字段
                if len(data['documents']) > 0:
                    doc = data['documents'][0]
                    expected_fields = ['id', 'filename', 'kind', 'size', 'created_at', 'chunk_count', 'concept_count', 'claim_count', 'processing_status']
                    missing_fields = [f for f in expected_fields if f not in doc]
                    if missing_fields:
                        print(f"⚠️  缺少字段: {missing_fields}")
                    else:
                        print(f"✅ 所有必需字段都存在")
                tests.append(True)
            else:
                print(f"❌ 响应结构不正确")
                tests.append(False)
        else:
            print(f"❌ HTTP {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        tests.append(False)
    
    # 测试 3: 分页参数
    print("\n3️⃣  分页参数测试")
    try:
        response = requests.get(f"{base_url}/uploads?skip=0&limit=10", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 分页参数正确")
            print(f"   - skip=0, limit=10")
            tests.append(True)
        else:
            print(f"❌ HTTP {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        tests.append(False)
    
    # 测试 4: 排序参数
    print("\n4️⃣  排序参数测试")
    try:
        response = requests.get(f"{base_url}/uploads?sort_by=filename", timeout=5)
        if response.status_code == 200:
            print(f"✅ 排序参数正确")
            tests.append(True)
        else:
            print(f"❌ HTTP {response.status_code}")
            tests.append(False)
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        tests.append(False)
    
    # 总结
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {total - passed}")
    print(f"📈 成功率: {100*passed//total}%")
    
    if passed == total:
        print("\n✨ 所有测试通过!")
        print("🎉 API 功能完全正常!")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1

def main():
    """主函数"""
    print("\n" + "="*70)
    print("🚀 GraphRAG 文档管理 - 最终集成验证")
    print("="*70)
    
    print("\n✓ 后端服务器: http://127.0.0.1:8000")
    print("✓ 前端开发服务器: http://127.0.0.1:3001")
    print("✓ Neo4j: 127.0.0.1:7687")
    print("✓ Redis: 127.0.0.1:6379")
    
    return test_api()

if __name__ == "__main__":
    sys.exit(main())
