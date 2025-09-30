# 合并API部署指南

## 概述

已将 `apiMain.py` 和 `agent_api.py` 合并为 `combined_api.py`，统一使用 FastAPI 框架，共用一个端口（5000）。

## 优势

1. **简化部署**：只需启动一个服务
2. **统一端口**：所有API接口都在同一个端口上
3. **统一框架**：使用 FastAPI，支持异步操作，性能更好
4. **统一管理**：任务状态、会话管理、OSS处理都在一个服务中

## 接口对比

### 原 apiMain.py 接口（保持不变）
- `POST /api/ai/sessions` - 创建会话
- `POST /api/ai/sessions/{sessionId}/messages` - 发送消息
- `GET /api/ai/sessions/{sessionId}/messages` - 查询消息
- `POST /api/ai/sessions/{sessionId}/end` - 结束会话
- `GET /api/ai/tasks/{taskId}` - 查询任务状态

### 原 agent_api.py 接口（迁移到新路径）
- `POST /api/ai/oss-tasks` - 提交OSS处理任务（原 `/submit-task`）
- `GET /api/ai/tasks/{taskId}` - 查询任务状态（与原接口合并）

### 新增接口
- `GET /health` - 健康检查
- `GET /` - API根路径

## 部署步骤

### 1. 环境准备
确保已安装以下依赖：
```bash
pip install fastapi uvicorn aiohttp requests dashscope redis
```

### 2. 启动Redis服务
```bash
# Windows
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:latest
```

### 3. 启动合并后的API服务
```bash
python combined_api.py
```

### 4. 验证服务
访问以下URL验证服务是否正常：
- http://localhost:5000/docs - API文档
- http://localhost:5000/health - 健康检查

## 接口使用示例

### 会话管理（原apiMain.py功能）
```bash
# 创建会话
curl -X POST "http://localhost:5000/api/ai/sessions" \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test123", "title": "测试会话"}'

# 发送消息
curl -X POST "http://localhost:5000/api/ai/sessions/test123/messages" \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test123", "messageId": "msg1", "content": "你好"}'

# 查询消息
curl "http://localhost:5000/api/ai/sessions/test123/messages?pageNum=1&pageSize=10"
```

### OSS处理（原agent_api.py功能）
```bash
# 提交OSS处理任务
curl -X POST "http://localhost:5000/api/ai/oss-tasks" \
  -H "Content-Type: application/json" \
  -d '{"signed_oss_url": "https://example.com/file.pdf"}'

# 查询任务状态（与消息处理任务使用同一个接口）
curl "http://localhost:5000/api/ai/tasks/{taskId}"
```

## 配置文件

确保 `.env` 文件中的端口配置正确：
```env
FASTAPI_PORT=5000
```

## 生产环境部署

### 使用 Gunicorn + Uvicorn（推荐）
```bash
pip install gunicorn
gunicorn combined_api:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000
```

### 使用 PM2（Node.js进程管理器）
```bash
npm install -g pm2
pm2 start combined_api.py --interpreter python --name "xinmai-api"
```

## 注意事项

1. **Redis依赖**：两个功能都依赖Redis存储数据，确保Redis服务正常运行
2. **阿里云百炼配置**：确保 `DASHSCOPE_API_KEY` 和 `BAILIAN_APP_ID` 配置正确
3. **LLM服务**：消息处理功能依赖本地LLM服务（8013端口）
4. **端口冲突**：合并后只使用5000端口，不会与其他服务冲突

## 故障排除

### 端口被占用
```bash
# 查看端口占用
netstat -ano | findstr :5000

# 杀死占用进程
taskkill /PID <PID> /F
```

### Redis连接失败
- 检查Redis服务是否启动
- 检查Redis配置是否正确

### 依赖包缺失
```bash
pip install -r requirements.txt
```

## 迁移说明

如果之前已经部署了单独的apiMain.py服务，迁移步骤：

1. 停止原有的apiMain.py服务
2. 备份原有数据（Redis中的数据会自动兼容）
3. 启动combined_api.py服务
4. 更新前端API调用地址（如果需要）

合并后的API完全兼容原有的接口规范，前端代码无需修改。
