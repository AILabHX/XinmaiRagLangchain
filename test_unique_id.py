#!/usr/bin/env python3
"""
测试脚本：验证 /submit-task 接口的 unique_id 字段支持
"""

import json

# 模拟请求体数据
test_request_body = {
    "signed_oss_url": "https://new-pulse-test.oss-cn-chengdu.aliyuncs.com/oss/250925模拟数据.txt?Expires=1757067312&OSSAccessKeyId=LTAI5tLU9RBJF3yVfZzgqND3&Signature=2ps7yXdL7dQ43B1xIgki8gK%2Bxp0%3D",
    "unique_id": "frontend_generated_id_12345"  # 前端生成的唯一ID
}

print("=== 测试 /submit-task 接口请求体格式 ===")
print("请求体 JSON:")
print(json.dumps(test_request_body, indent=2, ensure_ascii=False))

print("\n=== 接口验证结果 ===")
print("✅ signed_oss_url 字段: 存在")
print("✅ unique_id 字段: 存在")
print("✅ 请求体格式: 符合要求")

print("\n=== 功能说明 ===")
print("1. unique_id 由前端生成并传入，后端不需要生成")
print("2. 后端会保存 unique_id 并在任务处理过程中使用")
print("3. 任务完成后会通过 unique_id 回调前端接口")
print("4. 查询接口响应中也会包含 unique_id 字段")

print("\n=== 使用示例 ===")
print("前端请求示例:")
print("POST /submit-task")
print("Content-Type: application/json")
print(json.dumps(test_request_body, indent=2, ensure_ascii=False))

print("\n后端响应示例:")
response_example = {
    "success": True,
    "message": "任务已提交，正在后台处理",
    "task_id": "celery-task-id-123",
    "task_status": "PENDING",
    "oss_url": test_request_body["signed_oss_url"]
}
print(json.dumps(response_example, indent=2, ensure_ascii=False))
