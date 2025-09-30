# Webhook回调功能使用说明

## 概述

本功能为API网关添加了Webhook回调机制，允许客户端在发送消息时指定回调URL，当AI处理完成后，系统会自动向该URL发送回调通知，避免客户端需要轮询查询任务状态。

## 功能特点

- **立即返回**：API立即返回任务ID（202 Accepted状态）
- **异步处理**：AI处理在后台异步进行
- **主动通知**：处理完成后主动向回调URL发送通知
- **错误处理**：处理失败时也会发送错误回调
- **兼容性**：保持与现有API的完全兼容

## 使用方法

### 1. 发送消息时指定回调URL

在发送消息的请求体中添加`callbackUrl`字段：

```json
{
  "sessionId": "your-session-id",
  "messageId": "your-message-id",
  "content": "用户消息内容",
  "messageType": 0,
  "sendTime": "2024-01-01T12:00:00",
  "callbackUrl": "http://your-server:port/ai/message/receive"
}
```

### 2. API响应

API会立即返回任务信息：

```json
{
  "success": true,
  "message": "消息已接收，正在处理中",
  "data": {
    "taskId": "生成的唯一任务ID",
    "status": "processing",
    "userMessageId": "your-message-id"
  }
}
```

### 3. Webhook回调数据格式

当AI处理完成后，系统会向指定的回调URL发送POST请求，数据格式如下：

**成功回调：**
```json
{
  "sessionId": "your-session-id",
  "messageId": "your-message-id",
  "messageType": 0,
  "content": "AI回复内容"
}
```

**失败回调：**
```json
{
  "sessionId": "your-session-id",
  "messageId": "your-message-id",
  "messageType": 0,
  "content": "AI处理失败: 错误信息"
}
```

### 4. 客户端回调接口要求

客户端需要提供一个POST接口来接收回调，接口应返回200状态码表示接收成功：

```python
# Flask示例
@app.route('/ai/message/receive', methods=['POST'])
def receive_callback():
    data = request.get_json()
    # 处理回调数据
    print(f"收到AI回复: {data['content']}")
    return jsonify({"success": True, "message": "回调接收成功"})
```

## 测试环境配置

### 测试回调URL
- **回调路径**: `/ai/message/receive`
- **测试环境**: `http://10.0.0.19:9090`
- **完整URL**: `http://10.0.0.19:9090/ai/message/receive`

### 测试示例

```bash
# 启动API服务器
python apiMain.py

# 在另一个终端运行测试
python test_webhook.py
```

## 错误处理

### 回调失败处理
- 如果回调URL不可达或返回非200状态码，系统会记录警告日志
- 回调失败不会影响消息的正常处理和存储
- 客户端仍可通过任务状态查询接口获取结果

### 超时设置
- 回调请求超时时间为10秒
- 超时后不会重试，但会记录错误日志

## 日志监控

系统会记录Webhook回调的相关日志：

```
INFO - Webhook回调成功: http://10.0.0.19:9090/ai/message/receive
WARNING - Webhook回调失败: 500 - Internal Server Error
ERROR - Webhook回调异常: Connection refused
```

## 兼容性说明

### 向后兼容
- 不指定`callbackUrl`字段时，行为与之前完全一致
- 客户端仍可通过任务状态查询接口获取结果
- 现有代码无需任何修改即可继续使用

### 向前兼容
- 新增的`callbackUrl`字段为可选字段
- 不会破坏现有的API契约

## 最佳实践

1. **回调URL验证**：在生产环境中验证回调URL的有效性
2. **错误重试机制**：客户端应实现适当的错误重试逻辑
3. **幂等性处理**：确保回调处理是幂等的，避免重复处理
4. **安全考虑**：验证回调请求的来源，确保安全性

## 故障排除

### 常见问题

1. **回调未收到**
   - 检查回调URL是否正确
   - 检查网络连通性
   - 查看API服务器日志

2. **回调超时**
   - 检查客户端接口响应时间
   - 确认网络延迟情况

3. **回调数据格式不符**
   - 确认数据格式符合文档要求
   - 检查字符编码问题

### 调试工具

使用提供的`test_webhook.py`脚本进行功能测试和调试。

## 版本历史

- **v1.0** (2024-09-23): 初始版本，实现基本Webhook回调功能
- 支持成功/失败回调
- 异步处理机制
- 完整的错误处理
