#!/bin/bash
# 黄金策略回测 - 设置和运行脚本

echo "=========================================="
echo "黄金交易策略回测系统"
echo "=========================================="

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建完成"
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "正在安装依赖包..."
pip install pandas numpy --quiet
echo "✓ 依赖安装完成"

# 运行回测
echo ""
echo "=========================================="
echo "开始运行回测..."
echo "=========================================="
python run_backtest.py

# 退出虚拟环境
deactivate
