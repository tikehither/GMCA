#!/bin/bash

# CA Docker 停止脚本

echo "停止 CA 服务..."
docker-compose down

echo "清理未使用的资源..."
docker system prune -f

echo "服务已停止"