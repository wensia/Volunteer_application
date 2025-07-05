#!/bin/bash
# 重新部署脚本 - 修复数据库访问问题
# 在服务器上运行

echo "🚀 天津中考位次查询系统 - 重新部署"
echo "=================================="

# 1. 停止并删除旧容器
echo "🛑 停止旧容器..."
docker stop volunteer_app 2>/dev/null || echo "容器未运行"
docker rm volunteer_app 2>/dev/null || echo "容器不存在"

# 2. 清理旧镜像（可选）
echo "🗑️  清理旧镜像..."
docker rmi ghcr.io/wensia/volunteer_application:latest 2>/dev/null || echo "镜像不存在"

# 3. 拉取最新镜像
echo "📥 拉取最新镜像..."
docker pull ghcr.io/wensia/volunteer_application:latest

if [ $? -ne 0 ]; then
    echo "❌ 镜像拉取失败！"
    exit 1
fi

# 4. 启动新容器
echo "🚀 启动新容器..."
docker run -d \
    --name volunteer_app \
    --restart unless-stopped \
    -p 8008:8008 \
    ghcr.io/wensia/volunteer_application:latest

if [ $? -ne 0 ]; then
    echo "❌ 容器启动失败！"
    exit 1
fi

# 5. 等待容器启动
echo "⏳ 等待容器启动..."
sleep 10

# 6. 检查容器状态
echo "📋 检查容器状态..."
docker ps | grep volunteer_app

# 7. 检查容器日志
echo "📝 容器启动日志："
docker logs volunteer_app --tail 10

# 8. 测试API
echo "🧪 测试API..."
sleep 5

# 测试基本API
echo "测试 /api-info..."
curl -s "http://localhost:8008/api-info" | head -1

# 测试关键的 /rank API
echo "测试 /rank API..."
curl -s -X POST "http://localhost:8008/rank" \
     -H "Content-Type: application/json" \
     -d '{"score": 650}' | head -1

echo ""
echo "🎯 部署完成！"
echo "=================================="
echo "🌐 访问地址："
echo "  - API文档: http://39.98.86.6:8008/docs"
echo "  - 查询界面: http://39.98.86.6:8008/"
echo "  - API信息: http://39.98.86.6:8008/api-info"
echo ""
echo "🔧 如果仍有问题，运行："
echo "  docker logs volunteer_app"
echo "  docker exec -it volunteer_app ./container_check.sh" 