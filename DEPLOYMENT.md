# 🚀 天津中考位次查询系统 - 部署指南

## 📦 Docker镜像部署

### 镜像信息
- **镜像地址**: `ghcr.io/wensia/volunteer_application:latest`
- **仓库地址**: https://github.com/wensia/Volunteer_application
- **容器注册表**: GitHub Container Registry (ghcr.io)

## 🎯 快速部署（推荐）

### 方法一：使用部署脚本
```bash
# 1. 下载部署脚本
curl -O https://raw.githubusercontent.com/wensia/Volunteer_application/main/deploy.sh

# 2. 添加执行权限
chmod +x deploy.sh

# 3. 运行部署脚本
./deploy.sh
```

### 方法二：使用Docker Compose
```bash
# 1. 下载docker-compose.yml
curl -O https://raw.githubusercontent.com/wensia/Volunteer_application/main/docker-compose.yml

# 2. 启动服务
docker-compose up -d

# 3. 查看状态
docker-compose ps
```

## 🔧 手动部署

### 1. 拉取镜像
```bash
docker pull ghcr.io/wensia/volunteer_application:latest
```

### 2. 运行容器
```bash
docker run -d \
  --name volunteer-app \
  -p 8008:8008 \
  -e PORT=8008 \
  -e PYTHONUNBUFFERED=1 \
  --restart unless-stopped \
  ghcr.io/wensia/volunteer_application:latest
```

### 3. 验证部署
```bash
# 检查容器状态
docker ps

# 查看日志
docker logs volunteer-app

# 测试API
curl http://localhost:8008/api-info
```

## 🌐 访问应用

部署成功后，您可以通过以下地址访问：

- **主页**: http://localhost:8008
- **API文档**: http://localhost:8008/docs
- **健康检查**: http://localhost:8008/api-info
- **统计信息**: http://localhost:8008/stats

## 📊 容器管理

### 查看运行状态
```bash
docker ps --filter "name=volunteer-app"
```

### 查看日志
```bash
# 查看最近日志
docker logs volunteer-app

# 实时查看日志
docker logs -f volunteer-app
```

### 重启服务
```bash
docker restart volunteer-app
```

### 停止服务
```bash
docker stop volunteer-app
```

### 删除容器
```bash
docker stop volunteer-app
docker rm volunteer-app
```

### 更新应用
```bash
# 停止并删除旧容器
docker stop volunteer-app && docker rm volunteer-app

# 拉取最新镜像
docker pull ghcr.io/wensia/volunteer_application:latest

# 重新运行容器
docker run -d \
  --name volunteer-app \
  -p 8008:8008 \
  --restart unless-stopped \
  ghcr.io/wensia/volunteer_application:latest
```

## 🔐 环境变量

支持的环境变量：

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| PORT | 8008 | 应用端口 |
| PYTHONUNBUFFERED | 1 | Python输出缓冲 |
| PYTHONDONTWRITEBYTECODE | 1 | 禁止生成.pyc文件 |

## 🌟 生产环境建议

### 1. 使用反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8008;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 配置SSL证书
```bash
# 使用Let's Encrypt
certbot --nginx -d your-domain.com
```

### 3. 监控和日志
```bash
# 使用Docker Compose with logging
version: '3.8'
services:
  volunteer-app:
    image: ghcr.io/wensia/volunteer_application:latest
    ports:
      - "8008:8008"
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 🔧 故障排除

### 端口占用
```bash
# 查看端口使用情况
netstat -tulpn | grep :8008

# 或使用lsof
lsof -i :8008
```

### 容器无法启动
```bash
# 查看详细日志
docker logs volunteer-app

# 检查镜像是否存在
docker images | grep volunteer_application
```

### 健康检查失败
```bash
# 进入容器检查
docker exec -it volunteer-app /bin/bash

# 手动测试API
curl http://localhost:8008/api-info
```

## 📞 技术支持

如果遇到问题，请：

1. 查看容器日志：`docker logs volunteer-app`
2. 检查GitHub Actions构建状态
3. 提交Issue到GitHub仓库
4. 确保Docker和系统环境符合要求

## 🎉 成功部署标志

当您看到以下输出时，表示部署成功：

```
✅ 部署成功！

🎯 访问信息:
  - 应用地址: http://localhost:8008
  - API文档: http://localhost:8008/docs
  - 健康检查: http://localhost:8008/api-info
```

祝您使用愉快！🚀 