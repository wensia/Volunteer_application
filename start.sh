#!/bin/bash

# 天津中考位次查询系统启动脚本
# 统一使用端口8008

echo "==================================="
echo "天津中考位次查询系统"
echo "==================================="
echo ""

# 进入后端目录
cd backend

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误：未找到Python 3"
    exit 1
fi

# 检查uvicorn是否安装
if ! python3 -c "import uvicorn" &> /dev/null; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
fi

# 启动API服务器
echo "启动API服务器..."
echo "API地址: http://localhost:8008"
echo "API文档: http://localhost:8008/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "==================================="

# 启动服务
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8008