#!/bin/bash
# 测试套件快速运行脚本
# Quick Test Suite Runner

set -e

TESTS_DIR="../tests"
cd "$TESTS_DIR"

echo "=================================="
echo "POW_SE 测试套件快速运行"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 函数: 运行单个测试
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "${YELLOW}[运行]${NC} $test_name"
    echo "----------------------------------------"
    
    if python "$test_file"; then
        echo -e "${GREEN}✅ 通过${NC}"
    else
        echo -e "${RED}❌ 失败${NC}"
        return 1
    fi
    echo ""
}

# 菜单
echo "请选择测试类型:"
echo ""
echo "  1) 快速验证 (推荐首先运行)"
echo "  2) 领域优化验证"
echo "  3) 文档管理功能测试"
echo "  4) 图谱 API 测试"
echo "  5) 标准 pytest 测试"
echo "  6) 全部独立测试"
echo "  0) 退出"
echo ""
read -p "请输入选项 (0-6): " choice

case $choice in
    1)
        echo -e "\n${YELLOW}=== 快速验证 ===${NC}\n"
        run_test "verify_quick.py" "快速验证"
        ;;
    
    2)
        echo -e "\n${YELLOW}=== 领域优化验证 ===${NC}\n"
        run_test "test_domain_optimization.py" "领域过滤器验证"
        run_test "test_kg_optimization_integration.py" "图谱优化集成测试"
        ;;
    
    3)
        echo -e "\n${YELLOW}=== 文档管理功能测试 ===${NC}\n"
        run_test "test_documents_code.py" "代码验证"
        run_test "test_documents_neo4j.py" "Neo4j 查询测试"
        run_test "test_documents_integration.py" "集成检查"
        echo -e "${YELLOW}注意: 以下测试需要服务器运行${NC}"
        read -p "是否继续? (y/n): " continue_choice
        if [ "$continue_choice" = "y" ]; then
            run_test "test_documents_fullstack.py" "全栈集成测试"
            run_test "test_documents_final.py" "最终 API 验证"
        fi
        ;;
    
    4)
        echo -e "\n${YELLOW}=== 图谱 API 测试 ===${NC}\n"
        echo -e "${YELLOW}注意: 需要服务器运行${NC}"
        read -p "服务器是否已运行? (y/n): " server_running
        if [ "$server_running" = "y" ]; then
            run_test "test_graph_api.py" "图谱可视化 API"
        else
            echo -e "${RED}请先启动服务器: cd ../.. && python main.py${NC}"
        fi
        ;;
    
    5)
        echo -e "\n${YELLOW}=== 标准 pytest 测试 ===${NC}\n"
        cd ..
        echo "运行单元测试..."
        pytest -m unit -v
        echo ""
        echo "运行集成测试..."
        pytest -m integration -v
        echo ""
        echo "运行 API 测试..."
        pytest -m api -v
        ;;
    
    6)
        echo -e "\n${YELLOW}=== 全部独立测试 ===${NC}\n"
        run_test "verify_quick.py" "快速验证"
        run_test "test_domain_optimization.py" "领域过滤器验证"
        run_test "test_kg_optimization_integration.py" "图谱优化集成"
        run_test "test_documents_code.py" "文档代码验证"
        run_test "test_documents_neo4j.py" "文档 Neo4j 测试"
        run_test "test_documents_integration.py" "文档集成检查"
        
        echo -e "${YELLOW}注意: 以下测试需要服务器运行${NC}"
        read -p "服务器是否已运行? (y/n): " server_running
        if [ "$server_running" = "y" ]; then
            run_test "test_documents_fullstack.py" "文档全栈测试"
            run_test "test_documents_final.py" "文档最终验证"
            run_test "test_graph_api.py" "图谱 API 测试"
        else
            echo -e "${YELLOW}跳过需要服务器的测试${NC}"
        fi
        ;;
    
    0)
        echo "退出"
        exit 0
        ;;
    
    *)
        echo -e "${RED}无效选项${NC}"
        exit 1
        ;;
esac

echo ""
echo "=================================="
echo -e "${GREEN}测试运行完成!${NC}"
echo "=================================="
