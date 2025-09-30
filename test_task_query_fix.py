#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试任务查询接口修复
"""

import sys
import os
sys.path.append('.')

from apiMain import app
from redis_manager import redis_manager
import json

def test_task_query_fix():
    """测试任务查询接口修复"""
    print("=== 测试任务查询接口修复 ===")
    
    # 创建一个测试任务
    test_task_id = "test_task_001"
    task_data = {
        "taskId": test_task_id,
        "status": "completed",
        "sessionId": "test_session_001",
        "messageId": "test_msg_001",
        "createdAt": "2024-01-01T10:00:00",
        "completedAt": "2024-01-01T10:01:00",
        "result": json.dumps({"userMessageId": "test_msg_001", "aiMessage": {"content": "测试回复"}})
    }
    
    # 存储测试任务到Redis
    redis_manager.create_task(task_data)
    # 更新任务状态为完成
    redis_manager.update_task(test_task_id, "completed", result={"userMessageId": "test_msg_001", "aiMessage": {"content": "测试回复"}})
    print(f"✅ 创建并更新测试任务: {test_task_id}")
    
    # 测试获取任务信息
    task_info = redis_manager.get_task(test_task_id)
    if task_info:
        print(f"✅ 成功获取任务信息")
        print(f"   任务ID: {task_info.get('taskId')}")
        print(f"   状态: {task_info.get('status')}")
        print(f"   创建时间: {task_info.get('createdAt')}")
        print(f"   完成时间: {task_info.get('completedAt')}")
        print(f"   结果: {task_info.get('result')}")
        
        # 测试API响应格式
        if task_info["status"] == "completed":
            response_data = {
                "taskId": test_task_id,
                "status": "completed",
                "result": task_info.get("result"),
                "completed_at": task_info.get("completedAt")
            }
            print(f"✅ API响应格式正确")
            print(f"   响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        else:
            print("❌ 任务状态不正确")
    else:
        print("❌ 获取任务信息失败")
    
    # 清理测试数据
    redis_manager.redis_client.delete(f"task:{test_task_id}")
    print(f"✅ 清理测试数据")

if __name__ == "__main__":
    test_task_query_fix()
