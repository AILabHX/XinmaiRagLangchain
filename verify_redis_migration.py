#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis迁移验证脚本
验证从本地Redis迁移到阿里云Redis的完整功能
"""

import sys
import requests
import time
import json
from redis_manager import redis_manager

def test_redis_connection():
    """测试Redis连接"""
    print("=" * 50)
    print("1. 测试Redis连接")
    print("=" * 50)
    
    try:
        # 测试本地Redis
        print("正在测试本地Redis连接...")
        local_manager = redis_manager
        if hasattr(local_manager, 'redis') and local_manager.redis:
            print("✅ 本地Redis连接成功")
        else:
            print("❌ 本地Redis连接失败")
            return False
    except Exception as e:
        print(f"❌ 本地Redis连接失败: {e}")
        return False
    
    try:
        # 测试阿里云Redis
        print("正在测试阿里云Redis连接...")
        aliyun_manager = redis_manager.__class__(
            host='r-2vcvlqn3xxvgrh75hcpd.redis.cn-chengdu.rds.aliyuncs.com',
            port=6379,
            db=3,
            password='5IevEcX3C7BhLNZR'
        )
        aliyun_manager.redis.ping()
        print("✅ 阿里云Redis连接成功")
    except Exception as e:
        print(f"❌ 阿里云Redis连接失败: {e}")
        return False
    
    return True

def test_redis_operations():
    """测试Redis基本操作"""
    print("\n" + "=" * 50)
    print("2. 测试Redis基本操作")
    print("=" * 50)
    
    try:
        # 测试会话操作
        print("正在测试会话操作...")
        session_id = f"test-session-{int(time.time())}"
        session_data = {
            "sessionId": session_id,
            "title": "测试会话",
            "description": "Redis迁移测试",
            "consultType": "test"
        }
        
        if redis_manager.create_session(session_data):
            print("✅ 会话创建成功")
        else:
            print("❌ 会话创建失败")
            return False
        
        if redis_manager.session_exists(session_id):
            print("✅ 会话存在检查成功")
        else:
            print("❌ 会话存在检查失败")
            return False
        
        # 测试消息操作
        print("正在测试消息操作...")
        message_id = f"test-message-{int(time.time())}"
        message_data = {
            "messageId": message_id,
            "sessionId": session_id,
            "messageType": 0,
            "content": "这是一条测试消息",
            "sendTime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sender": "user"
        }
        
        if redis_manager.add_message(session_id, message_data):
            print("✅ 消息添加成功")
        else:
            print("❌ 消息添加失败")
            return False
        
        # 测试任务操作
        print("正在测试任务操作...")
        task_id = f"test-task-{int(time.time())}"
        task_data = {
            "taskId": task_id,
            "status": "completed",
            "sessionId": session_id,
            "messageId": message_id,
            "createdAt": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if redis_manager.create_task(task_data):
            print("✅ 任务创建成功")
        else:
            print("❌ 任务创建失败")
            return False
        
        if redis_manager.update_task(task_id, "completed"):
            print("✅ 任务更新成功")
        else:
            print("❌ 任务更新失败")
            return False
        
        # 清理测试数据
        redis_manager.delete_session(session_id)
        print("✅ 测试数据清理完成")
        
    except Exception as e:
        print(f"❌ Redis操作测试失败: {e}")
        return False
    
    return True

def test_api_service():
    """测试API服务"""
    print("\n" + "=" * 50)
    print("3. 测试API服务")
    print("=" * 50)
    
    try:
        # 测试健康检查
        print("正在测试API健康检查...")
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API健康检查成功")
        else:
            print(f"❌ API健康检查失败: {response.status_code}")
            return False
        
        # 测试API文档
        print("正在测试API文档...")
        response = requests.get("http://localhost:5000/docs", timeout=5)
        if response.status_code == 200:
            print("✅ API文档访问成功")
        else:
            print(f"❌ API文档访问失败: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ API服务测试失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("Redis迁移验证脚本")
    print("=" * 50)
    
    # 执行所有测试
    tests = [
        ("Redis连接", test_redis_connection),
        ("Redis操作", test_redis_operations),
        ("API服务", test_api_service)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！Redis迁移成功！")
        print("\n部署说明：")
        print("1. 在阿里云Windows服务器上运行 deploy_windows.bat")
        print("2. 编辑 .env 文件配置阿里云Redis参数")
        print("3. 启动API服务: python apiMain.py")
        print("4. 访问 http://localhost:5000/docs 验证")
    else:
        print("❌ 部分测试失败，请检查配置和网络连接")
    print("=" * 50)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
