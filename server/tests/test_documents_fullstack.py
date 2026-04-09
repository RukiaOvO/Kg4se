#!/usr/bin/env python3
"""完整的集成测试 - 测试文档管理功能的各个部分"""

import sys
import time
import subprocess
import requests
import json
from pathlib import Path

def wait_for_server(url="http://localhost:8000", timeout=30):
    """等待服务器启动"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{url}/docs", timeout=2)
            if response.status_code == 200:
                print(f"✅ 服务器已启动 (耗时 {time.time() - start:.1f}秒)")
                return True
        except:
            pass
        time.sleep(1)
    print(f"❌ 服务器启动超时 ({timeout}秒)")
    return False

def test_api_endpoints():
    """测试 API 端点"""
    print("\n" + "="*60)
    print("🧪 API 端点测试")
    print("="*60)
    
    base_url = "http://localhost:8000"
    
    # 测试列表端点
    print("\n1️⃣  测试 GET /uploads (文档列表)")
    try:
        response = requests.get(f"{base_url}/uploads?skip=0&limit=50")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 响应成功")
            print(f"   - 总文档数: {data.get('total', 0)}")
            print(f"   - 返回文档数: {len(data.get('documents', []))}")
            if 'documents' in data and len(data['documents']) > 0:
                doc = data['documents'][0]
                print(f"   - 文档字段: {list(doc.keys())}")
            return True
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_frontend_types():
    """测试前端类型定义"""
    print("\n" + "="*60)
    print("📝 前端类型定义检查")
    print("="*60)
    
    services_ts = Path("../../app/vue/src/api/services.ts")
    if not services_ts.exists():
        print("❌ services.ts 不存在")
        return False
    
    content = services_ts.read_text(encoding='utf-8')
    
    checks = {
        "DocumentListResponse 类型": "export interface DocumentListResponse",
        "DocumentDetail 类型": "export interface DocumentDetail",
        "listDocuments 函数": "export const listDocuments =",
        "getDocumentDetail 函数": "export const getDocumentDetail =",
        # "listDocuments 函数": "export async function listDocuments",
        # "getDocumentDetail 函数": "export async function getDocumentDetail",
    }
    
    all_ok = True
    for name, pattern in checks.items():
        if pattern in content:
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
            all_ok = False
    
    return all_ok

def test_frontend_component():
    """测试前端组件"""
    print("\n" + "="*60)
    print("🎨 前端组件检查")
    print("="*60)
    
    documents_vue = Path("../../app/vue/src/views/Documents.vue")
    if not documents_vue.exists():
        print("❌ Documents.vue 不存在")
        return False
    
    content = documents_vue.read_text(encoding='utf-8')
    
    checks = {
        "数据表组件": "<n-data-table",
        "加载函数": "loadDocuments()",
        "分页": "pagination",
        "排序": "sortBy",
        "详情抽屉": "<n-modal",
        "统计卡片": "totalDocuments",
    }
    
    all_ok = True
    for name, pattern in checks.items():
        if pattern in content:
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
            all_ok = False
    
    return all_ok

def test_backend_endpoints():
    """测试后端端点实现"""
    print("\n" + "="*60)
    print("🔧 后端端点检查")
    print("="*60)
    
    upload_py = Path("../routes/upload.py")
    if not upload_py.exists():
        print("❌ upload.py 不存在")
        return False
    
    content = upload_py.read_text(encoding='utf-8')
    
    checks = {
        "list_documents 端点": "async def list_documents",
        "get_document 端点": "async def get_document",
        "路由装饰器": "@router.get",
        "文档查询": "MATCH (d:Document)",
        "分页支持": "skip",
        "排序支持": "sort_by",
    }
    
    all_ok = True
    for name, pattern in checks.items():
        if pattern in content:
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
            all_ok = False
    
    return all_ok

def test_routing():
    """测试路由配置"""
    print("\n" + "="*60)
    print("🛣️  路由配置检查")
    print("="*60)
    
    router_ts = Path("../../app/vue/src/router/index.ts")
    if not router_ts.exists():
        print("❌ router/index.ts 不存在")
        return False
    
    content = router_ts.read_text(encoding='utf-8')
    
    if "documents" in content.lower() and "Documents" in content:
        print("✅ /documents 路由已配置")
        return True
    else:
        print("❌ /documents 路由未配置")
        return False

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 GraphRAG 文档管理 - 完整集成测试")
    print("="*60)
    
    all_results = []
    
    # 1. 检查代码实现
    print("\n📋 代码实现检查")
    print("-" * 60)
    all_results.append(("后端端点", test_backend_endpoints()))
    all_results.append(("前端类型", test_frontend_types()))
    all_results.append(("前端组件", test_frontend_component()))
    all_results.append(("路由配置", test_routing()))
    
    # 2. 启动服务器并测试 API
    print("\n🚀 启动 FastAPI 服务器...")
    server_process = subprocess.Popen(
        ["python3", "main.py"],
        cwd="..",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if wait_for_server():
        print("\n🌐 API 集成测试")
        print("-" * 60)
        all_results.append(("API 端点", test_api_endpoints()))
    else:
        print("❌ 服务器启动失败，跳过 API 测试")
        all_results.append(("API 端点", False))
    
    # 清理
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()
    
    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)
    
    for name, result in all_results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    passed = sum(1 for _, r in all_results if r)
    total = len(all_results)
    
    print(f"\n📈 通过率: {passed}/{total} ({100*passed//total}%)")
    
    if passed == total:
        print("\n✨ 所有测试通过!")
        print("🎉 文档管理功能实现完成!")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试未通过")
        return 1

if __name__ == "__main__":
    sys.exit(main())
