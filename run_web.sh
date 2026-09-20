#!/bin/bash
# 一键启动基于 React 的本地家庭财富规划工作台 (数据存储于 localStorage)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

PORT=3000
echo "🚀 正在启动本地 React 家庭财务规划工具 (目标导向规划模块)..."
echo "📂 项目主入口: file://$SCRIPT_DIR/index.html"
echo "🌐 本地 Web 服务即将启动在: http://localhost:$PORT"

# 优先尝试在 macOS 上直接用默认浏览器打开 index.html
if command -v open >/dev/null 2>&1; then
    open "http://localhost:$PORT" || open "$SCRIPT_DIR/index.html"
fi

# 启动本地静态 HTTP 服务器
python3 -m http.server $PORT
