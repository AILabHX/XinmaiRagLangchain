#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试API任务查询接口
"""

import requests
import json
import time

def test_task_query_api():
    """测试任务查询API接口"""
    base_url = "http://localhost:5001"
    
    print("=== 测试任务查询API接口 ===")
    
    # 1. 首先创建一个会话
    session_data = {
        "sessionId": "test_session_api_001",
        "title": "测试会话",
        "description": "用于测试任务查询API",
        "consultType": "健康咨询"
    }
    
    print("1. 创建会话...")
    response = requests.post(f"{base_url}/api/ai/sessions", json=session_data)
    print(f"   响应: {response.status_code} - {response.json()}")
    
    # 2. 发送消息创建任务
    message_data = {
        "sessionId": "test_session_api_001",
        "messageId": "test_msg_api_001",
        "content": "饭后脚疼",
        "messageType": 0,
        "sendTime": ""
    }
    
    print("2. 发送消息创建任务...")
    response = requests.post(f"{base_url}/api/ai/sessions/test_session_api_001/messages", json=message_data)
    print(f"   响应: {response.status_code}")
    
    if response.status_code == 202:
        task_info = response.json()
        task_id = task_info["data"]["taskId"]
        print(f"   任务ID: {task_id}")
        
        # 3. 查询任务状态
        print("3. 查询任务状态...")
        time.sleep(2)  # 等待一下让任务开始处理
        
        response = requests.get(f"{base_url}/api/ai/tasks/{task_id}")
        print(f"   响应: {response.status_code}")
        
        if response.status_code == 200:
            task_status = response.json()
            print(f"   任务状态: {json.dumps(task_status, indent=2, ensure_ascii=False)}")
            
            # 检查响应格式是否正确
            if task_status["success"]:
                data = task_status["data"]
                if "taskId" in data and "status" in data:
                    print("✅ 任务查询接口修复成功！")
                    print(f"   任务ID: {data['taskId']}")
                    print(f"   状态: {data['status']}")
                    
                    if data["status"] == "completed":
                        print(f"   完成时间: {data.get('completed_at', 'N/A')}")
                        print(f"   结果: {data.get('result', 'N/A')}")
                    elif data["status"] == "failed":
                        print(f"   失败时间: {data.get('failed_at', 'N/A')}")
                        print(f"   错误: {data.get('error', 'N/A')}")
                    else:
                        print(f"   创建时间: {data.get('created_at', 'N/A')}")
                else:
                    print("❌ 响应格式不正确")
            else:
                print(f"❌ 任务查询失败: {task_status['message']}")
        else:
            print(f"❌ 任务查询失败: {response.status_code}")
    else:
        print(f"❌ 发送消息失败: {response.status_code}")

if __name__ == "__main__":
    test_task_query_api()
