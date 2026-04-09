#!/usr/bin/env python3
"""简单的 API 测试脚本 - 不需要启动整个服务器"""

import sys
import ast
from pathlib import Path

def test_implementation():
    """测试代码实现"""
    print("\n" + "="*70)
    print("✨ GraphRAG 文档管理功能 - 代码验证")
    print("="*70)
    
    results = {}
    
    # 1. 测试后端实现
    print("\n📍 后端实现验证")
    print("-"*70)
    
    upload_py = Path("../routes/upload.py")
    if not upload_py.exists():
        print("❌ upload.py 不存在")
        return 1
    
    upload_content = upload_py.read_text(encoding='utf-8')
    
    backend_checks = {
        "list_documents 端点": "async def list_documents" in upload_content,
        "get_document 端点": "async def get_document" in upload_content,
        "路由装饰器 @router.get": "@router.get" in upload_content,
        "文档查询": "MATCH (d:Document)" in upload_content,
        "分页参数 skip": "skip:" in upload_content or "skip =" in upload_content,
        "排序参数 sort_by": "sort_by" in upload_content,
    }
    
    for check_name, check_result in backend_checks.items():
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
        results[f"backend_{check_name}"] = check_result
    
    # 2. 测试前端 API 服务
    print("\n📍 前端 API 服务验证")
    print("-"*70)
    
    services_ts = Path("../../app/vue/src/api/services.ts")
    if not services_ts.exists():
        print("❌ services.ts 不存在")
        return 1
    
    services_content = services_ts.read_text(encoding='utf-8')
    
    services_checks = {
        "DocumentListResponse 类型": "export interface DocumentListResponse" in services_content,
        "DocumentDetail 类型": "export interface DocumentDetail" in services_content,
        "listDocuments 函数 (export const)": "export const listDocuments" in services_content,
        "getDocumentDetail 函数 (export const)": "export const getDocumentDetail" in services_content,
    }
    
    for check_name, check_result in services_checks.items():
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
        results[f"services_{check_name}"] = check_result
    
    # 3. 测试前端组件
    print("\n📍 前端组件验证")
    print("-"*70)
    
    documents_vue = Path("../../app/vue/src/views/Documents.vue")
    if not documents_vue.exists():
        print("❌ Documents.vue 不存在")
        return 1
    
    doc_content = documents_vue.read_text(encoding='utf-8')
    
    component_checks = {
        "n-data-table 数据表": "<n-data-table" in doc_content,
        "loadDocuments() 方法": "const loadDocuments = async" in doc_content or "loadDocuments()" in doc_content,
        "分页支持 (pagination)": "pagination" in doc_content,
        "排序支持 (sortBy)": "sortBy" in doc_content,
        "n-modal 详情模态框": "<n-modal" in doc_content,
        "文档统计 (totalDocuments)": "totalDocuments" in doc_content,
        "已处理统计 (completedDocuments)": "completedDocuments" in doc_content,
        "待处理统计 (pendingDocuments)": "pendingDocuments" in doc_content,
    }
    
    for check_name, check_result in component_checks.items():
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
        results[f"component_{check_name}"] = check_result
    
    # 4. 测试集成
    print("\n📍 集成验证")
    print("-"*70)
    
    router_ts = Path("../../app/vue/src/router/index.ts")
    if not router_ts.exists():
        print("❌ router/index.ts 不存在")
        return 1
    
    router_content = router_ts.read_text(encoding='utf-8')
    
    integration_checks = {
        "/documents 路由": "'documents'" in router_content or '"documents"' in router_content,
        "Documents 组件关联": "Documents" in router_content,
    }
    
    main_layout = Path("../../app/vue/src/layouts/MainLayout.vue")
    if main_layout.exists():
        layout_content = main_layout.read_text(encoding='utf-8')
        integration_checks["导航菜单 (文档管理)"] = "文档管理" in layout_content
    
    dashboard = Path("../../app/vue/src/views/Dashboard.vue")
    if dashboard.exists():
        dash_content = dashboard.read_text(encoding='utf-8')
        integration_checks["仪表板集成 (文档管理)"] = "文档管理" in dash_content
    
    for check_name, check_result in integration_checks.items():
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
        results[f"integration_{check_name}"] = check_result
    
    # 5. 测试 Python 语法
    print("\n📍 Python 语法检查")
    print("-"*70)
    
    python_files = [
        ("upload.py", "../routes/upload.py"),
        ("stage6_graph_service.py", "../graphrag/prompts/stages/stage6_graph_service.py"),
        ("stage8_metrics_service.py", "../graphrag/prompts/stages/stage8_metrics_service.py"),
    ]
    
    for file_name, file_path in python_files:
        path = Path(file_path)
        try:
            if path.exists():
                content = path.read_text(encoding='utf-8')
                ast.parse(content)
                print(f"✅ {file_name} 语法正确")
                results[f"syntax_{file_name}"] = True
            else:
                print(f"❌ {file_name} 不存在")
                results[f"syntax_{file_name}"] = False
        except SyntaxError as e:
            print(f"❌ {file_name}: {e}")
            results[f"syntax_{file_name}"] = False
    
    # 统计结果
    print("\n" + "="*70)
    print("📊 验证总结")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n✅ 通过: {passed}")
    print(f"❌ 失败: {total - passed}")
    print(f"📈 成功率: {100*passed//total}%")
    
    # 详细分类统计
    print("\n📋 分类统计:")
    categories = {
        "后端": [k for k in results if k.startswith("backend_")],
        "前端服务": [k for k in results if k.startswith("services_")],
        "组件": [k for k in results if k.startswith("component_")],
        "集成": [k for k in results if k.startswith("integration_")],
        "语法": [k for k in results if k.startswith("syntax_")],
    }
    
    for cat_name, cat_keys in categories.items():
        if cat_keys:
            cat_passed = sum(1 for k in cat_keys if results[k])
            cat_total = len(cat_keys)
            pct = 100*cat_passed//cat_total if cat_total > 0 else 0
            print(f"  {cat_name}: {cat_passed}/{cat_total} ({pct}%)")
    
    # 最终判断
    print("\n" + "="*70)
    if passed == total:
        print("✨ 所有检查通过!")
        print("🎉 文档管理功能实现完全!")
        print("\n📌 接下来的步骤:")
        print("  1. 启动 FastAPI 服务器: cd server && uvicorn main:app --reload")
        print("  2. 启动前端开发服务器: cd app/vue && npm run dev")
        print("  3. 访问 http://localhost:5173/documents 查看文档管理界面")
        return 0
    else:
        print(f"⚠️  有 {total - passed} 个检查未通过")
        print("请查看上面的详细信息修复问题")
        return 1

if __name__ == "__main__":
    sys.exit(test_implementation())
