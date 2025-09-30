#!/bin/bash

# XinMai-RagLangChain 部署脚本
# 适用于阿里云CentOS服务器

set -e

echo "=== XinMai-RagLangChain 部署脚本 ==="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "Docker未安装，开始安装Docker..."
    # 安装Docker
    sudo yum install -y yum-utils
    sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo yum install -y docker-ce docker-ce-cli containerd.io
    sudo systemctl start docker
    sudo systemctl enable docker
    echo "Docker安装完成"
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose未安装，开始安装..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose安装完成"
fi

# 使用当前目录作为项目目录
PROJECT_DIR=$(pwd)
echo "使用当前目录作为项目目录: $PROJECT_DIR"

# 检查项目文件是否在当前目录
echo "检查当前目录的项目文件..."
echo "项目应包含以下文件："
echo "- mainMemory.py"
echo "- apiMain.py" 
echo "- requirements_XM.txt"
echo "- prompt_template_memory.txt"
echo "- chromaDB/ 目录（向量数据库）"
echo "- input/ 目录（输入文件）"
echo "- memory.db（SQLite数据库）"

# 检查必要的文件
if [ ! -f "mainMemory.py" ] || [ ! -f "apiMain.py" ]; then
    echo "错误：缺少必要的Python文件"
    exit 1
fi

# 检查部署配置文件是否在当前目录
echo "检查部署配置文件..."
if [ ! -f "Dockerfile" ]; then
    echo "错误：Dockerfile不存在"
    exit 1
fi
if [ ! -f "docker-compose.yml" ]; then
    echo "错误：docker-compose.yml不存在"
    exit 1
fi
if [ ! -f ".env" ]; then
    echo "警告：.env文件不存在，请创建并配置API密钥"
fi

# 配置环境变量
echo "请编辑 .env 文件配置您的API密钥和其他设置："
echo "vim .env"

# 构建Docker镜像
echo "开始构建Docker镜像..."
docker-compose build

# 启动服务
echo "启动服务..."
docker-compose up -d

echo "=== 部署完成 ==="
echo "服务已启动："
echo "- API服务: http://localhost:5000"
echo "- LLM服务: http://localhost:8013"
echo ""
echo "查看日志：docker-compose logs -f"
echo "停止服务：docker-compose down"
echo "重启服务：docker-compose restart"
