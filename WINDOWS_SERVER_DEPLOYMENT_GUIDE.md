# Windows服务器部署指南

## 概述

本指南详细说明如何在阿里云Windows服务器上部署XinMai-RagLangChain项目，包括Redis迁移到阿里云Redis服务的完整配置。

## 环境要求

- Windows Server 2019/2022
- Python 3.8+
- Git
- 阿里云Redis实例访问权限

## 部署步骤

### 1. 项目准备

```bash
# 克隆项目
git clone https://github.com/AILabHX/XinmaiRagLangchain.git
cd XinmaiRagLangchain

# 创建Python虚拟环境
python -m venv api_env
api_env\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 环境配置

将 `.env.production.template` 文件重命名为 `.env`：

```bash
copy .env.production.template .env
```

编辑 `.env` 文件，确保以下Redis配置正确：

```env
# 生产环境Redis配置（阿里云）
REDIS_HOST=r-2vcvlqn3xxvgrh75hcpd.redis.cn-chengdu.rds.aliyuncs.com
REDIS_PORT=6379
REDIS_PASSWORD=5IevEcX3C7BhLNZR
REDIS_DB=3

# 其他配置保持不变
OPENAI_API_KEY=your_openai_api_key
PROJECT_ROOT=D:\Work\Project\XinMai-RagLangChain
```

### 3. 项目路径配置

在 `apiMain.py` 中，确保 `PROJECT_ROOT` 路径正确指向项目目录：

```python
# 在 apiMain.py 中修改项目根路径
PROJECT_ROOT = r"D:\Work\Project\XinMai-RagLangChain"  # 根据实际路径修改
```

### 4. 测试阿里云Redis连接

```bash
python test_aliyun_redis.py
```

预期输出应该显示阿里云Redis连接成功。

### 5. 启动API服务

```bash
python apiMain.py
```

服务将在 `http://localhost:5000` 启动。

### 6. 验证部署

使用浏览器或API测试工具访问：
- `http://localhost:5000/docs` - API文档
- `http://localhost:5000/health` - 健康检查

## 防火墙配置

确保Windows防火墙允许以下端口：
- 5000 (API服务端口)
- 6379 (Redis连接端口，如果需要在服务器本地访问)

## 生产环境优化

### 1. 使用Windows服务运行

创建Windows服务来运行API：

```powershell
# 创建服务脚本 run_api.bat
@echo off
cd /d D:\Work\Project\XinMai-RagLangChain
call api_env\Scripts\activate
python apiMain.py

# 使用nssm创建Windows服务
nssm install XinMaiAPI "D:\Work\Project\XinMai-RagLangChain\run_api.bat"
nssm set XinMaiAPI DisplayName "XinMai API Service"
nssm set XinMaiAPI Description "XinMai RAG LangChain API Service"
nssm start XinMaiAPI
```

### 2. 日志配置

项目使用Python logging模块，日志文件位于：
- `logs/` 目录（如果配置了文件日志）
- 控制台输出

### 3. 监控和健康检查

定期检查：
- API服务状态：`http://localhost:5000/health`
- Redis连接状态：运行 `test_redis_connection.py`

## 故障排除

### 常见问题

1. **Redis连接失败**
   - 检查阿里云Redis白名单设置
   - 验证密码和数据库编号
   - 确认网络连通性

2. **API服务无法启动**
   - 检查Python环境是否正确激活
   - 验证依赖是否完整安装
   - 检查端口5000是否被占用

3. **路径问题**
   - 确保所有文件路径使用Windows格式（反斜杠）
   - 验证PROJECT_ROOT路径正确

### 日志分析

查看日志文件或控制台输出，重点关注：
- Redis连接状态
- API启动过程
- 任何错误或异常信息

## 安全注意事项

1. **环境变量安全**
   - 不要将 `.env` 文件提交到版本控制
   - 定期轮换Redis密码
   - 保护OpenAI API密钥

2. **网络安全**
   - 配置阿里云安全组规则
   - 限制Redis访问IP白名单
   - 使用HTTPS进行生产环境API访问

## 备份和恢复

### 数据备份
- Redis数据：阿里云Redis自动备份
- 项目配置：备份 `.env` 文件
- 向量数据库：备份 `chromaDB/` 目录

### 恢复流程
1. 恢复项目代码
2. 恢复环境配置（`.env`）
3. 恢复向量数据库
4. 重启服务

## 联系方式

如有部署问题，请联系技术支持团队。
