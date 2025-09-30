# Dify Chatflow 集成指南

## 修改概述

已将 `mainMemory.py` 中的 LLM 模型从 LangChain 替换为 Dify Chatflow API，实现了架构简化和功能增强。

## 主要修改内容

### 1. 架构变化

**修改前：**
- LangChain + ChatOpenAI + ChromaDB + 本地RAG
- 复杂的LCEL chain构建
- 本地向量检索和对话历史管理

**修改后：**
- 直接HTTP调用Dify Chatflow API
- Dify处理所有RAG功能
- 简化的API调用架构

### 2. 文件修改

#### mainMemory.py
- **移除**：所有LangChain相关代码（ChatOpenAI、ChatPromptTemplate、RunnableWithMessageHistory等）
- **移除**：ChromaDB向量库初始化
- **移除**：本地向量检索逻辑
- **新增**：`call_dify_api()` 函数处理Dify API调用
- **新增**：`generate_dify_stream()` 函数处理流式响应
- **保留**：原有的FastAPI接口格式，确保兼容性

#### .env
- **新增**：`DIFY_API_KEY=your_dify_api_key_here` 配置项

#### requirements.txt
- **新增**：`httpx==0.27.0` 依赖包

#### 新增文件
- `test_dify_integration.py` - Dify API集成测试脚本

### 3. 配置要求

#### 必需的环境变量
```bash
DIFY_API_KEY=your_actual_dify_api_key
```

#### Dify服务配置
```python
DIFY_API_BASE = "http://192.168.96.1/v1"  # Dify服务地址
DIFY_CHAT_ENDPOINT = "/chat-messages"     # Chatflow API端点
```

### 4. API接口保持兼容

修改后的服务仍然提供相同的API接口：

**请求格式（不变）：**
```json
POST /v1/chat/completions
{
  "messages": [
    {"role": "user", "content": "用户问题"}
  ],
  "stream": false,
  "userId": "用户ID",
  "conversationId": "对话ID"
}
```

**响应格式（不变）：**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "回答内容"
      },
      "finish_reason": "stop"
    }
  ]
}
```

### 5. 优势

1. **架构简化**：从500+行代码减少到200+行
2. **维护更容易**：不再需要管理本地向量库
3. **功能更强大**：直接利用Dify内置的RAG功能
4. **性能更好**：减少本地检索开销
5. **扩展性更好**：Dify的知识库管理更方便

### 6. 部署步骤

1. **配置环境变量**
   ```bash
   # 在.env文件中设置正确的DIFY_API_KEY
   DIFY_API_KEY=your_actual_dify_api_key
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **测试连接**
   ```bash
   python test_dify_integration.py
   ```

4. **启动服务**
   ```bash
   python mainMemory.py
   ```

5. **验证功能**
   - 访问 `http://localhost:8013/health` 检查服务状态
   - 使用API客户端测试 `/v1/chat/completions` 接口

### 7. 故障排除

#### 常见问题

1. **DIFY_API_KEY未设置**
   - 症状：服务启动失败
   - 解决：在.env文件中设置正确的DIFY_API_KEY

2. **Dify服务连接失败**
   - 症状：API调用返回连接错误
   - 解决：检查Dify服务地址和网络连接

3. **认证失败**
   - 症状：API返回401错误
   - 解决：检查DIFY_API_KEY是否正确

4. **流式响应问题**
   - 症状：流式响应不工作
   - 解决：检查Dify的response_mode设置

### 8. 测试验证

使用提供的测试脚本：
```bash
python test_dify_integration.py
```

该脚本会：
- 验证Dify API连接
- 测试基本对话功能
- 检查RAG检索结果

## 总结

本次修改成功将复杂的LangChain架构替换为简洁的Dify Chatflow API调用，在保持API兼容性的同时大幅简化了代码结构，提高了系统的可维护性和扩展性。
