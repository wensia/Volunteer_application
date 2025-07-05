#!/bin/bash

echo "🚀 天津中考位次查询系统 - 部署脚本"
echo "======================================"

# 设置变量
IMAGE_NAME="ghcr.io/wensia/volunteer_application:latest"
CONTAINER_NAME="volunteer-app"
PORT=8008

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装。请先安装Docker。"
    exit 1
fi

# 检查是否已有运行的容器
if docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "📋 发现已存在的容器，正在停止和删除..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

# 拉取最新镜像
echo "📦 正在拉取最新镜像..."
docker pull $IMAGE_NAME

if [ $? -ne 0 ]; then
    echo "❌ 镜像拉取失败。请检查网络连接。"
    exit 1
fi

# 运行容器
echo "🚀 正在启动容器..."
docker run -d \
  --name $CONTAINER_NAME \
  -p $PORT:$PORT \
  -e PORT=$PORT \
  -e PYTHONUNBUFFERED=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  --restart unless-stopped \
  $IMAGE_NAME

if [ $? -eq 0 ]; then
    echo "✅ 部署成功！"
    echo ""
    echo "🎯 访问信息:"
    echo "  - 应用地址: http://localhost:$PORT"
    echo "  - API文档: http://localhost:$PORT/docs"
    echo "  - 健康检查: http://localhost:$PORT/api-info"
    echo ""
    echo "📊 容器状态:"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "📝 常用命令:"
    echo "  查看日志: docker logs $CONTAINER_NAME"
    echo "  停止服务: docker stop $CONTAINER_NAME"
    echo "  重启服务: docker restart $CONTAINER_NAME"
    echo "  删除容器: docker rm $CONTAINER_NAME"
else
    echo "❌ 部署失败！"
    exit 1
fi 