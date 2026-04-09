#!/usr/bin/env python3
"""综合集成验证脚本 - 验证文档管理功能实现"""

import sys
import os
import ast
import json
from pathlib import Path

def check_backend_implementation():
    """检查后端实现"""
    print("\n" + "="*60)
    print("📋 检查后端实现")
    print("="*60)
    
    upload_py = Path("../routes/upload.py")
    if not upload_py.exists():
        print("❌ 错误: upload.py 不存在")
        return False
    
    content = upload_py.read_text()
    
    # 检查是否有 list_documents 端点
    if "async def list_documents" in content:
        print("✅ 发现 list_documents() 端点")
    else:
        print("❌ 缺少 list_documents() 端点")
        return False
    
    # 检查是否有 get_document 端点
    if "async def get_document" in content:
        print("✅ 发现 get_document() 端点")
    else:
        print("❌ 缺少 get_document() 端点")
        return False
    
    # 检查 Cypher 查询
    if "MATCH (d:Document)" in content:
        print("✅ 包含 Document 查询")
    else:
        print("❌ 缺少 Document 查询")
        return False
    
    # 检查 API 路由装饰器
    if "@router.get" in content and "list_documents" in content:
        print("✅ list_documents 有路由装饰器")
    else:
        print("❌ list_documents 缺少路由装饰器")
        return False
    
    return True

def check_frontend_implementation():
    """检查前端实现"""
    print("\n" + "="*60)
    print("🎨 检查前端实现")
    print("="*60)
    
    # 检查 API 服务
    services_ts = Path("../../app/vue/src/api/services.ts")
    if not services_ts.exists():
        print("❌ 错误: services.ts 不存在")
        return False
    
    content = services_ts.read_text()
    
    if "listDocuments" in content:
        print("✅ services.ts 有 listDocuments() 函数")
    else:
        print("❌ services.ts 缺少 listDocuments() 函数")
        return False
    
    if "getDocumentDetail" in content:
        print("✅ services.ts 有 getDocumentDetail() 函数")
    else:
        print("❌ services.ts 缺少 getDocumentDetail() 函数")
        return False
    
    if "DocumentListResponse" in content:
        print("✅ services.ts 定义了 DocumentListResponse 类型")
    else:
        print("❌ services.ts 缺少 DocumentListResponse 类型")
        return False
    
    if "DocumentDetail" in content:
        print("✅ services.ts 定义了 DocumentDetail 类型")
    else:
        print("❌ services.ts 缺少 DocumentDetail 类型")
        return False
    
    # 检查 Vue 组件
    documents_vue = Path("../../app/vue/src/views/Documents.vue")
    if not documents_vue.exists():
        print("❌ 错误: Documents.vue 不存在")
        return False
    
    print("✅ Documents.vue 组件存在")
    
    content = documents_vue.read_text()
    
    if "loadDocuments" in content:
        print("✅ Documents.vue 有 loadDocuments() 方法")
    else:
        print("❌ Documents.vue 缺少 loadDocuments() 方法")
        return False
    
    if "n-data-table" in content.lower():
        print("✅ Documents.vue 使用了数据表组件")
    else:
        print("❌ Documents.vue 缺少数据表")
        return False
    
    if "n-drawer" in content.lower() or "n-modal" in content.lower():
        print("✅ Documents.vue 有详情展示组件")
    else:
        print("❌ Documents.vue 缺少详情展示")
        return False
    
    # 检查路由
    router_ts = Path("../../app/vue/src/router/index.ts")
    if not router_ts.exists():
        print("❌ 错误: router/index.ts 不存在")
        return False
    
    content = router_ts.read_text()
    
    if "'documents'" in content or '"documents"' in content:
        print("✅ 路由配置中有 /documents 路径")
    else:
        print("❌ 路由配置缺少 /documents 路径")
        return False
    
    if "Documents.vue" in content or "Documents" in content:
        print("✅ 路由关联了 Documents 组件")
    else:
        print("❌ 路由未关联 Documents 组件")
        return False
    
    # 检查导航集成
    main_layout = Path("../../app/vue/src/layouts/MainLayout.vue")
    if not main_layout.exists():
        print("❌ 错误: MainLayout.vue 不存在")
        return False
    
    content = main_layout.read_text()
    
    if "文档管理" in content or "documents" in content.lower():
        print("✅ MainLayout 包含文档管理菜单")
    else:
        print("⚠️  MainLayout 可能未包含文档管理菜单")
    
    return True

def check_documentation():
    """检查文档"""
    print("\n" + "="*60)
    print("📚 检查文档")
    print("="*60)
    
    doc_file = Path("../../DOCUMENTS_FEATURE_GUIDE.md")
    if doc_file.exists():
        print("✅ 存在功能指南文档")
        lines = doc_file.read_text().split('\n')
        print(f"   📄 文档行数: {len(lines)}")
    else:
        print("⚠️  缺少功能指南文档")
    
    test_file = Path("../../test_documents_api.py")
    if test_file.exists():
        print("✅ 存在 API 测试脚本")
        lines = test_file.read_text().split('\n')
        print(f"   🧪 测试脚本行数: {len(lines)}")
    else:
        print("⚠️  缺少 API 测试脚本")
    
    return True

def check_python_syntax():
    """检查 Python 代码语法"""
    print("\n" + "="*60)
    print("🔍 检查 Python 语法")
    print("="*60)
    
    python_files = [
        "../routes/upload.py",
        "../graphrag/stages/stage6_graph_service.py",
        "../graphrag/stages/stage8_metrics_service.py",
    ]
    
    all_ok = True
    for file_path in python_files:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  {path.name} 不存在")
            continue
        
        try:
            content = path.read_text()
            ast.parse(content)
            print(f"✅ {path.name} 语法正确")
        except SyntaxError as e:
            print(f"❌ {path.name} 有语法错误: {e}")
            all_ok = False
    
    return all_ok

def check_feature_completeness():
    """检查功能完整性"""
    print("\n" + "="*60)
    print("✨ 功能完整性检查")
    print("="*60)
    
    features = {
        "文档列表 API": False,
        "文档详情 API": False,
        "前端列表视图": False,
        "前端详情模态框": False,
        "路由配置": False,
        "导航集成": False,
        "仪表板集成": False,
        "类型定义": False,
    }
    
    # 检查后端
    upload_py = Path("../routes/upload.py").read_text()
    if "async def list_documents" in upload_py:
        features["文档列表 API"] = True
    if "async def get_document" in upload_py:
        features["文档详情 API"] = True
    
    # 检查前端
    documents_vue = Path("../../app/vue/src/views/Documents.vue")
    if documents_vue.exists():
        content = documents_vue.read_text()
        if "loadDocuments" in content:
            features["前端列表视图"] = True
        if "n-drawer" in content.lower() or "n-modal" in content.lower():
            features["前端详情模态框"] = True
    
    # 检查路由
    router_ts = Path("../../app/vue/src/router/index.ts").read_text()
    if "documents" in router_ts.lower():
        features["路由配置"] = True
    
    # 检查导航
    main_layout = Path("../../app/vue/src/layouts/MainLayout.vue").read_text()
    if "文档管理" in main_layout:
        features["导航集成"] = True
    
    # 检查仪表板
    dashboard = Path("../../app/vue/src/views/Dashboard.vue")
    if dashboard.exists():
        content = dashboard.read_text()
        if "文档管理" in content:
            features["仪表板集成"] = True
    
    # 检查类型
    services_ts = Path("../../app/vue/src/api/services.ts").read_text()
    if "DocumentListResponse" in services_ts and "DocumentDetail" in services_ts:
        features["类型定义"] = True
    
    for feature, completed in features.items():
        status = "✅" if completed else "❌"
        print(f"{status} {feature}")
    
    completed_count = sum(1 for v in features.values() if v)
    print(f"\n📊 完成度: {completed_count}/{len(features)} ({100*completed_count//len(features)}%)")
    
    return completed_count == len(features)

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 GraphRAG 文档管理功能验证")
    print("="*60)
    
    checks = [
        ("后端实现", check_backend_implementation),
        ("前端实现", check_frontend_implementation),
        ("文档", check_documentation),
        ("Python 语法", check_python_syntax),
        ("功能完整性", check_feature_completeness),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} 检查失败: {e}")
            results.append((name, False))
    
    # 总结
    print("\n" + "="*60)
    print("📋 验证总结")
    print("="*60)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    all_ok = all(r for _, r in results)
    
    print("\n" + "="*60)
    if all_ok:
        print("✨ 所有检查通过!")
        print("🎉 文档管理功能实现完成!")
    else:
        print("⚠️  某些检查未通过，请查看上面的详细信息")
    print("="*60 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
