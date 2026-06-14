#!/bin/bash
# 自动激活虚拟环境并启动 Streamlit 仪表盘
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "⚠️ 未找到虚拟环境 .venv，正在创建并安装依赖..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install streamlit pandas plotly
fi

echo "🚀 正在启动红利低波现金流规划仪表盘..."
.venv/bin/streamlit run app.py
