#!/usr/bin/env python3
"""
集成测试：验证知识图谱优化的实际效果
Integration Test: Verify Knowledge Graph Optimization Results
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# Add server to path
sys.path.insert(0, "..")

def test_entity_type_validation():
    """测试实体类型验证"""
    print("\n" + "="*60)
    print("测试 1: 实体类型验证 (Entity Type Validation)")
    print("="*60)
    
    try:
        from graphrag.stages.stage6_graph_service import ALLOWED_ENTITY_TYPES
        
        print(f"\n✅ 允许的实体类型 ({len(ALLOWED_ENTITY_TYPES)} 种):")
        for entity_type in sorted(ALLOWED_ENTITY_TYPES):
            print(f"   • {entity_type}")
        
        # 测试验证
        test_types = [
            ("KnowledgePoint", True),
            ("Content", True),
            ("Document", True),
            ("Question", True),
            ("Timestamp", True),
            ("Person", False),
            ("Organization", False),
            ("Method", False),
            ("Tool", False),
        ]
        
        print("\n实体类型验证测试:")
        passed = 0
        for entity_type, should_pass in test_types:
            is_allowed = entity_type in ALLOWED_ENTITY_TYPES
            expected = is_allowed == should_pass
            status = "✅" if expected else "❌"
            print(f"   {status} {entity_type}: {'允许' if is_allowed else '过滤'}")
            if expected:
                passed += 1
        
        print(f"\n结果: {passed}/{len(test_types)} 通过")
        return passed == len(test_types)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_relationship_type_validation():
    """测试关系类型验证"""
    print("\n" + "="*60)
    print("测试 2: 关系类型验证 (Relationship Type Validation)")
    print("="*60)
    
    try:
        from graphrag.stages.stage6_graph_service import ALLOWED_RELATIONSHIP_TYPES
        
        print(f"\n✅ 允许的关系类型 ({len(ALLOWED_RELATIONSHIP_TYPES)} 种):")
        for rel_type in sorted(ALLOWED_RELATIONSHIP_TYPES):
            print(f"   • {rel_type}")
        
        # 测试验证
        test_rels = [
            ("BELONGS_TO", True),
            ("FROM", True),
            ("PRACTICES_IS", True),
            ("HAS_TIMESTAMP", True),
            ("IS", True),
            ("USES", False),
            ("IMPLEMENTS_BY", False),
            ("CREATES", False),
            ("IS_A", False),
        ]
        
        print("\n关系类型验证测试:")
        passed = 0
        for rel_type, should_pass in test_rels:
            is_allowed = rel_type in ALLOWED_RELATIONSHIP_TYPES
            expected = is_allowed == should_pass
            status = "✅" if expected else "❌"
            print(f"   {status} {rel_type}: {'允许' if is_allowed else '过滤'}")
            if expected:
                passed += 1
        
        print(f"\n结果: {passed}/{len(test_rels)} 通过")
        return passed == len(test_rels)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_predicate_allowlist():
    """测试谓词白名单"""
    print("\n" + "="*60)
    print("测试 3: 谓词白名单 (Predicate Allowlist)")
    print("="*60)
    
    try:
        from graphrag.stages.stage5_predicate_governor import ALLOWED_PREDICATES
        
        print(f"\n✅ 允许的谓词 ({len(ALLOWED_PREDICATES)} 种):")
        for predicate in sorted(ALLOWED_PREDICATES):
            print(f"   • {predicate}")
        
        # 验证必须的 5 种谓词都存在
        required = {"BELONGS_TO", "FROM", "PRACTICES_IS", "HAS_TIMESTAMP", "IS"}
        all_present = required.issubset(ALLOWED_PREDICATES)
        
        print(f"\n必需谓词检查:")
        for pred in sorted(required):
            status = "✅" if pred in ALLOWED_PREDICATES else "❌"
            print(f"   {status} {pred}")
        
        print(f"\n结果: {'✅ 通过' if all_present else '❌ 失败'}")
        return all_present
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_domain_filter_keywords():
    """测试领域过滤器关键词"""
    print("\n" + "="*60)
    print("测试 4: 领域过滤器关键词 (Domain Filter Keywords)")
    print("="*60)
    
    try:
        # 不导入实际模块，直接检查文件内容
        domain_filter_path = Path("../graphrag/utils/domain_filter.py")
        content = domain_filter_path.read_text(encoding='utf-8')
        
        # 检查关键词库的存在
        if "SOFTWARE_ENGINEERING_KEYWORDS" in content:
            print("✅ 关键词库已定义")
        else:
            print("❌ 关键词库未找到")
            return False
        
        # 检查一些常见关键词
        common_keywords = [
            "singleton", "factory", "observer", "strategy",  # Design patterns
            "array", "list", "tree", "graph",                # Data structures
            "sorting", "searching", "dynamic",               # Algorithms
            "inheritance", "polymorphism", "encapsulation",  # OOP
            "unit_test", "integration_test",                 # Testing
            "microservices", "distributed_system",           # Architecture
        ]
        
        print("\n常见关键词检查:")
        found_count = 0
        for keyword in common_keywords:
            # 检查关键词是否在文件中（可能带引号或其他格式）
            if keyword in content or f'"{keyword}"' in content or f"'{keyword}'" in content:
                print(f"   ✅ {keyword}")
                found_count += 1
            else:
                print(f"   ⚠️  {keyword} (未在内容中找到)")
        
        print(f"\n结果: {found_count}/{len(common_keywords)} 关键词被找到")
        return found_count >= len(common_keywords) * 0.8  # 80% 以上即可
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_confidence_threshold():
    """测试置信度阈值"""
    print("\n" + "="*60)
    print("测试 5: 置信度阈值 (Confidence Threshold)")
    print("="*60)
    
    try:
        domain_filter_path = Path("../graphrag/utils/domain_filter.py")
        content = domain_filter_path.read_text(encoding='utf-8')
        
        # 查找阈值定义
        if "CONFIDENCE_THRESHOLD" in content:
            print("✅ 置信度阈值已定义")
            
            # 提取阈值值
            for line in content.split('\n'):
                if "CONFIDENCE_THRESHOLD" in line and "=" in line:
                    print(f"   定义: {line.strip()}")
                    # 检查阈值是否为 0.3 或其他合理值
                    if "0.3" in line or "0.25" in line or "0.4" in line:
                        print("   ✅ 阈值设置合理")
                        return True
        else:
            print("❌ 置信度阈值未定义")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_type_constraints():
    """测试类型约束"""
    print("\n" + "="*60)
    print("测试 6: 关系类型约束 (Type Constraints)")
    print("="*60)
    
    try:
        domain_filter_path = Path("../graphrag/utils/domain_filter.py")
        content = domain_filter_path.read_text(encoding='utf-8')
        
        # 检查类型约束的存在
        if "TYPE_CONSTRAINTS" in content:
            print("✅ 类型约束字典已定义")
        else:
            print("❌ 类型约束字典未找到")
            return False
        
        # 验证 5 种关系的约束
        constraints_to_check = [
            "BELONGS_TO",
            "FROM",
            "PRACTICES_IS",
            "HAS_TIMESTAMP",
            "IS"
        ]
        
        print("\n关系约束检查:")
        found = 0
        for constraint in constraints_to_check:
            if constraint in content:
                print(f"   ✅ {constraint}")
                found += 1
            else:
                print(f"   ❌ {constraint}")
        
        print(f"\n结果: {found}/{len(constraints_to_check)} 约束被定义")
        return found == len(constraints_to_check)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_config_files():
    """测试配置文件"""
    print("\n" + "="*60)
    print("测试 7: 配置文件 (Configuration Files)")
    print("="*60)
    
    tests_passed = 0
    total_tests = 2
    
    # 测试 ontology.yaml
    print("\n1. ontology.yaml 检查:")
    ontology_path = Path("../graphrag/config/ontology.yaml")
    if ontology_path.exists():
        content = ontology_path.read_text(encoding='utf-8')
        
        entities_found = 0
        entities = ["KnowledgePoint", "Content", "Document", "Question", "Timestamp"]
        for entity in entities:
            if entity in content:
                print(f"   ✅ {entity}")
                entities_found += 1
            else:
                print(f"   ❌ {entity}")
        
        if entities_found == 5:
            print(f"   ✅ 所有 5 种实体已定义")
            tests_passed += 1
        else:
            print(f"   ❌ 仅找到 {entities_found}/5 种实体")
    
    # 测试 predicates.yaml
    print("\n2. predicates.yaml 检查:")
    predicates_path = Path("../graphrag/config/predicates.yaml")
    if predicates_path.exists():
        content = predicates_path.read_text(encoding='utf-8')
        
        # 检查关键设置
        checks = [
            ("software-engineering" in content, "版本: software-engineering"),
            ("reject" in content, "策略: reject"),
            ("enabled: false" in content, "auto_expand: false"),
        ]
        
        config_ok = 0
        for check, desc in checks:
            if check:
                print(f"   ✅ {desc}")
                config_ok += 1
            else:
                print(f"   ❌ {desc}")
        
        if config_ok == len(checks):
            print(f"   ✅ 所有配置正确")
            tests_passed += 1
        else:
            print(f"   ❌ {len(checks) - config_ok} 项配置不正确")
    
    return tests_passed == total_tests

def generate_test_report(results: Dict[str, bool]) -> str:
    """生成测试报告"""
    report = "\n" + "="*60 + "\n"
    report += "测试总结 (Test Summary)\n"
    report += "="*60 + "\n"
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*60)
    print(f"总计: {passed}/{total} 通过")
    print(f"通过率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("\n🎉 所有测试通过！优化实施完成！")
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查上述错误")
    
    print("="*60)
    
    return report

def main():
    """主测试函数"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║  知识图谱优化集成测试 (Knowledge Graph Optimization Integration Test)" + " "*5 + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = {
        "实体类型验证": test_entity_type_validation(),
        "关系类型验证": test_relationship_type_validation(),
        "谓词白名单": test_predicate_allowlist(),
        "领域过滤关键词": test_domain_filter_keywords(),
        "置信度阈值": test_confidence_threshold(),
        "关系类型约束": test_type_constraints(),
        "配置文件": test_config_files(),
    }
    
    generate_test_report(tests)
    
    all_passed = all(tests.values())
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
