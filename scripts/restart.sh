#!/bin/bash

# CA Docker 重启脚本

echo "重启 CA 服务..."
docker-compose restart

echo "查看服务状态..."
docker-compose ps

echo "服务已重启"