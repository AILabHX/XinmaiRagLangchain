# XinMai-RagLangChain Docker 部署指南

## 项目概述

XinMai-RagLangChain 是一个基于 LangChain 和 FastAPI 的 RAG（检索增强生成）健康咨询系统，包含两个主要服务：

1. **mainMemory.py** - LLM 服务（端口 8013）：提供基于知识库的问答服务
2. **apiMain.py** - API 网关服务（端口 5000）：提供 RESTful API 接口

## 部署前准备

### 1. 服务器要求
- 阿里云 CentOS 7/8 服务器
- 至少 4GB RAM
- 至少 20GB 存储空间
- 开放端口：5000, 8013

### 2. 环境配置
在部署前，需要配置以下环境变量（编辑 `.env` 文件）：

```bash
# OneAPI配置（推荐）
ONEAPI_API_BASE=http://your_oneapi_server:3000/v1
ONEAPI_CHAT_API_KEY=your_oneapi_chat_key
ONEAPI_CHAT_MODEL=qwen-plus
ONEAPI_EMBEDDING_API_KEY=your_oneapi_embedding_key
ONEAPI_EMBEDDING_MODEL=text-embedding-v1

# 或 OpenAI配置（备用）
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_CHAT_API_KEY=your_openai_chat_key
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_API_KEY=your_openai_embedding_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# LangChain配置
LANGCHAIN_API_KEY=your_langchain_api_key

# API类型选择
API_TYPE=oneapi  # 或 openai
```

## 部署步骤

### 方法一：使用自动化脚本部署

1. **上传项目文件到服务器**
   ```bash
   scp -r ./* user@your_server_ip:/tmp/xinmai-rag/
   ```

2. **登录服务器并执行部署**
   ```bash
   ssh user@your_server_ip
   mkdir -p /opt/xinmai-rag
   cp -r /tmp/xinmai-rag/* /opt/xinmai-rag/
   cd /opt/xinmai-rag
   ```

3. **运行部署脚本**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

4. **配置环境变量**
   ```bash
   vim .env
   # 编辑配置文件，填入实际的API密钥
   ```

5. **重新启动服务**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### 方法二：手动部署

1. **安装 Docker 和 Docker Compose**
   ```bash
   # 安装 Docker
   sudo yum install -y yum-utils
   sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   sudo yum install -y docker-ce docker-ce-cli containerd.io
   sudo systemctl start docker
   sudo systemctl enable docker

   # 安装 Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **创建项目目录并上传文件**
   ```bash
   sudo mkdir -p /opt/xinmai-rag
   sudo chown -R $(whoami):$(whoami) /opt/xinmai-rag
   cd /opt/xinmai-rag

   # 上传所有项目文件到此目录
   ```

3. **构建和启动服务**
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## 验证部署

### 检查服务状态
```bash
docker-compose ps
docker-compose logs -f
```

### 测试 API 服务
```bash
# 测试 API 网关
curl http://localhost:5000/api/ai/sessions

# 测试 LLM 服务
curl -X POST http://localhost:8013/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}],
    "stream": false
  }'
```

## 文件说明

### 必需文件
- `mainMemory.py` - 主要的 LLM 服务
- `apiMain.py` - API 网关服务
- `requirements_XM.txt` - Python 依赖
- `prompt_template_memory.txt` - 提示词模板
- `chromaDB/` - 向量数据库目录
- `memory.db` - SQLite 对话历史数据库
- `input/` - 输入文档目录

### 部署文件
- `Dockerfile` - Docker 构建配置
- `docker-compose.yml` - Docker Compose 配置
- `.env` - 环境变量配置
- `deploy.sh` - 自动化部署脚本

## 日常运维

### 启动/停止服务
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

### 查看日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f xinmai-rag
```

### 更新部署
```bash
# 拉取最新代码后重新构建
docker-compose down
docker-compose build
docker-compose up -d
```

## 故障排除

### 常见问题

1. **端口冲突**
   - 检查端口 5000 和 8013 是否被占用
   - 修改 `docker-compose.yml` 中的端口映射

2. **API 密钥错误**
   - 检查 `.env` 文件中的 API 密钥配置
   - 确保网络可以访问 API 服务

3. **数据库文件权限**
   - 确保 `chromaDB/` 和 `memory.db` 有读写权限

4. **依赖安装失败**
   - 检查网络连接
   - 尝试使用国内镜像源

### 获取帮助
如果遇到问题，请检查日志文件：
```bash
docker-compose logs
```

## 安全建议

1. **修改默认端口** - 在生产环境中使用非标准端口
2. **配置防火墙** - 只开放必要的端口
3. **使用 HTTPS** - 配置 SSL 证书
4. **定期备份** - 备份 `chromaDB/` 和 `memory.db` 文件
5. **监控资源** - 监控 CPU、内存和磁盘使用情况

## 性能优化

1. **增加资源** - 根据负载调整 Docker 资源限制
2. **使用 GPU** - 如果使用本地模型，配置 GPU 支持
3. **缓存优化** - 配置 Redis 等缓存服务
4. **负载均衡** - 使用多个实例进行负载均衡
