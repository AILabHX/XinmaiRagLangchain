# 唯一识别ID字段实现说明

## 功能概述
在 `/submit-task` 接口中添加了 `unique_id` 字段支持，用于前端确认是否收到了OSS文件。

## 实现详情

### 1. 请求体格式更新
**原请求体：**
```json
{
  "signed_oss_url": "https://new-pulse-test.oss-cn-chengdu.aliyuncs.com/oss/250925模拟数据.txt?Expires=1757067312&OSSAccessKeyId=LTAI5tLU9RBJF3yVfZzgqND3&Signature=2ps7yXdL7dQ43B1xIgki8gK%2Bxp0%3D"
}
```

**新请求体：**
```json
{
  "signed_oss_url": "https://new-pulse-test.oss-cn-chengdu.aliyuncs.com/oss/250925模拟数据.txt?Expires=1757067312&OSSAccessKeyId=LTAI5tLU9RBJF3yVfZzgqND3&Signature=2ps7yXdL7dQ43B1xIgki8gK%2Bxp0%3D",
  "unique_id": "前端生成的唯一ID"
}
```

### 2. 后端处理逻辑

#### `/submit-task` 接口 (`agent_api.py`)
- **参数验证**：检查请求体必须包含 `signed_oss_url` 和 `unique_id`
- **任务提交**：将 `unique_id` 传递给异步任务
- **立即响应**：返回任务ID和初始状态

#### 异步任务处理 (`async_process_oss_data`)
- **接收参数**：接收 `unique_id` 参数
- **状态更新**：在任务状态中包含 `unique_id`
- **回调前端**：任务完成后使用 `unique_id` 回调前端接口

#### 查询接口 (`/query-task/<task_id>`)
- **响应包含**：在查询结果中包含 `unique_id` 字段
- **状态跟踪**：支持前端通过 `unique_id` 跟踪任务状态

### 3. 前端回调机制
- **回调接口**：`/advisor/ai/report/complete`
- **回调数据**：`{"unique_id": "前端生成的唯一ID"}`
- **配置方式**：通过环境变量 `FRONTEND_CALLBACK_URL` 配置

## 使用流程

### 前端操作步骤：
1. **生成唯一ID**：前端生成一个唯一识别ID（如UUID）
2. **提交任务**：调用 `/submit-task` 接口，包含 `unique_id`
3. **接收回调**：等待后端处理完成后回调通知
4. **查询状态**：可选，通过任务ID查询详细状态

### 后端处理流程：
1. **接收请求**：验证 `signed_oss_url` 和 `unique_id`
2. **提交任务**：将任务提交到Celery队列
3. **异步处理**：Worker处理OSS数据并调用智能体
4. **回调前端**：处理完成后通过 `unique_id` 回调前端

## 代码变更

### 主要修改文件：`agent_api.py`

#### 1. `/submit-task` 接口
```python
# 参数验证
if not request_data or "signed_oss_url" not in request_data or "unique_id" not in request_data:
    return jsonify({
        "success": False,
        "message": "请求参数缺失，需包含signed_oss_url和unique_id"
    }), 400

# 任务提交
task = async_process_oss_data.delay(signed_oss_url, unique_id)
```

#### 2. 异步任务定义
```python
@celery.task(bind=True, track_started=True)
def async_process_oss_data(self, signed_oss_url, unique_id=None):
    # 在任务状态中包含 unique_id
    self.update_state(state="PROGRESS", meta={
        "status": "开始处理OSS数据",
        "oss_url": signed_oss_url,
        "unique_id": unique_id,  # 新增
        "step": 1,
        "total_steps": 3
    })
    
    # 任务完成后回调前端
    if unique_id:
        callback_success = callback_frontend(unique_id)
```

#### 3. 查询接口响应
```python
# 在查询响应中包含 unique_id
response = {
    "success": True,
    "task_id": task_id,
    "task_state": task.state,
    "unique_id": task.info.get("unique_id"),  # 新增
    # ... 其他字段
}
```

## 环境配置

### 可选环境变量
```bash
# 前端回调接口URL（可选，默认：http://localhost:3000/advisor/ai/report/complete）
FRONTEND_CALLBACK_URL=http://your-frontend-domain/advisor/ai/report/complete
```

## 测试验证

运行测试脚本验证功能：
```bash
python test_unique_id.py
```

## 总结

✅ **功能已实现**：
- 请求体支持 `unique_id` 字段
- 后端正确处理和传递 `unique_id`
- 任务完成后自动回调前端
- 查询接口返回 `unique_id` 信息

✅ **符合要求**：
- `unique_id` 由前端生成，后端不需要生成
- 支持前端确认是否收到OSS文件
- 提供完整的状态跟踪机制
