# 使用官方Python运行时作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANGCHAIN_TRACING_V2=true

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY requirements_XM.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements_XM.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p chromaDB input other test tools

# 暴露端口
EXPOSE 5000 8013

# 设置启动命令
CMD ["sh", "-c", "uvicorn mainMemory:app --host 0.0.0.0 --port 8013 & uvicorn apiMain:app --host 0.0.0.0 --port 5000"]
