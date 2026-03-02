#!/bin/bash

# CA Docker 启动脚本

set -e

echo "========================================"
echo "CA 证书管理系统 Docker 部署脚本"
echo "========================================"

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi

# 检查环境文件
if [ ! -f .env ]; then
    echo "警告: .env 文件不存在，使用示例配置"
    cp .env.example .env
    echo "请编辑 .env 文件设置实际配置"
fi

# 创建必要的目录
mkdir -p logs keys certificates performance_test/test_results
mkdir -p mysql/init

# 设置目录权限
chmod -R 755 logs keys certificates

# 停止并删除现有容器
echo "清理现有容器..."
docker-compose down -v --remove-orphans || true

# 构建镜像
echo "构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 检查服务状态
echo "检查服务状态..."
docker-compose ps

# 显示日志
echo "显示最近日志..."
docker-compose logs --tail=20

echo "========================================"
echo "部署完成！"
echo ""
echo "服务访问地址："
echo "- MySQL: localhost:3306 (root/rootpassword)"
echo "- Server API: http://localhost:8888"
echo "- Client GUI: 通过 Docker 容器运行"
echo ""
echo "管理命令："
echo "- 查看日志: docker-compose logs -f"
echo "- 停止服务: docker-compose down"
echo "- 重启服务: docker-compose restart"
echo "- 进入容器:"
echo "  Server: docker exec -it ca-server bash"
echo "  Client: docker exec -it ca-client bash"
echo "  MySQL: docker exec -it ca-mysql mysql -u root -p"
echo ""
echo "初始化步骤："
echo "1. 等待 MySQL 完全启动（约30秒）"
echo "2. Server 会自动初始化数据库"
echo "3. Client 可以通过 GUI 连接"
echo "========================================"