#!/bin/bash

# 天津中考位次查询系统停止脚本
# 停止运行在端口8008的后端服务

echo "==================================="
echo "天津中考位次查询系统 - 停止服务"
echo "==================================="
echo ""

# 检查端口8008是否有服务在运行
PORT=8008
PID=$(lsof -ti:$PORT)

if [ -z "$PID" ]; then
    echo "❌ 未发现端口 $PORT 上运行的服务"
    echo ""
else
    echo "🔍 发现端口 $PORT 上的进程: $PID"
    
    # 尝试优雅停止
    echo "📝 尝试优雅停止服务..."
    kill -TERM $PID 2>/dev/null
    
    # 等待3秒让服务优雅关闭
    sleep 3
    
    # 检查进程是否还在运行
    if kill -0 $PID 2>/dev/null; then
        echo "⚠️  服务未响应优雅停止，强制终止..."
        kill -KILL $PID 2>/dev/null
        sleep 1
        
        # 再次检查
        if kill -0 $PID 2>/dev/null; then
            echo "❌ 无法停止进程 $PID"
            exit 1
        else
            echo "✅ 服务已强制停止"
        fi
    else
        echo "✅ 服务已优雅停止"
    fi
fi

# 清理可能残留的uvicorn进程
echo "🧹 清理相关进程..."
UVICORN_PIDS=$(ps aux | grep 'uvicorn.*api:app' | grep -v grep | awk '{print $2}')

if [ -n "$UVICORN_PIDS" ]; then
    echo "🔍 发现uvicorn进程: $UVICORN_PIDS"
    echo $UVICORN_PIDS | xargs kill -TERM 2>/dev/null
    sleep 2
    
    # 强制清理仍在运行的进程
    REMAINING_PIDS=$(ps aux | grep 'uvicorn.*api:app' | grep -v grep | awk '{print $2}')
    if [ -n "$REMAINING_PIDS" ]; then
        echo "⚠️  强制终止残留进程: $REMAINING_PIDS"
        echo $REMAINING_PIDS | xargs kill -KILL 2>/dev/null
    fi
fi

# 最终检查
sleep 1
FINAL_PID=$(lsof -ti:$PORT)
if [ -z "$FINAL_PID" ]; then
    echo "✅ 端口 $PORT 已释放"
    echo "🎉 后端服务已完全停止"
else
    echo "❌ 仍有进程占用端口 $PORT: $FINAL_PID"
    echo "请手动检查: sudo lsof -i:$PORT"
    exit 1
fi

echo ""
echo "==================================="
echo "停止完成！"
echo "可以重新运行 ./start.sh 来启动服务"
echo "===================================" 