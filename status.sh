#!/bin/bash

# 天津中考位次查询系统状态检查脚本
# 检查端口8008上的服务运行状态

echo "==================================="
echo "天津中考位次查询系统 - 服务状态"
echo "==================================="
echo ""

PORT=8008
API_URL="http://localhost:$PORT"

# 检查端口是否被占用
PID=$(lsof -ti:$PORT 2>/dev/null)

if [ -z "$PID" ]; then
    echo "❌ 服务状态: 未运行"
    echo "🔌 端口 $PORT: 空闲"
    echo ""
    echo "💡 启动服务: ./start.sh"
else
    echo "✅ 服务状态: 运行中"
    echo "🔌 端口 $PORT: 进程 $PID"
    
    # 检查进程详情
    PROCESS_INFO=$(ps -p $PID -o pid,cmd --no-headers 2>/dev/null)
    if [ -n "$PROCESS_INFO" ]; then
        echo "📋 进程信息: $PROCESS_INFO"
    fi
    
    # 测试API连通性
    echo ""
    echo "🌐 测试API连通性..."
    
    if command -v curl &> /dev/null; then
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health" --connect-timeout 5 --max-time 10 2>/dev/null)
        
        if [ "$HTTP_STATUS" = "200" ]; then
            echo "✅ API响应: 正常 (HTTP $HTTP_STATUS)"
            
            # 获取API信息
            API_INFO=$(curl -s "$API_URL/" --connect-timeout 5 --max-time 10 2>/dev/null)
            if [ $? -eq 0 ] && [ -n "$API_INFO" ]; then
                echo "📊 API信息: 可访问"
            fi
        elif [ "$HTTP_STATUS" = "000" ]; then
            echo "⚠️  API响应: 连接超时或拒绝连接"
        else
            echo "⚠️  API响应: HTTP $HTTP_STATUS"
        fi
    else
        echo "⚠️  无法测试API（未安装curl）"
    fi
    
    echo ""
    echo "🔗 服务地址:"
    echo "   API: $API_URL"
    echo "   文档: $API_URL/docs"
    echo ""
    echo "💡 停止服务: ./stop.sh"
    echo "💡 重启服务: ./restart.sh"
fi

echo ""
echo "===================================" 