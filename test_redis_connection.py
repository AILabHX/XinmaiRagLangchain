#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis连接测试脚本
用于验证Redis服务器连接和基本功能
支持环境变量配置，可测试本地Redis和阿里云Redis
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_manager import RedisManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 创建新的Redis管理器实例，支持环境变量配置
redis_manager = RedisManager()

def test_redis_connection():
    """测试Redis连接"""
    try:
        # 测试连接
        redis_manager.redis_client.ping()
        logger.info("✅ Redis连接测试成功")
        return True
    except Exception as e:
        logger.error(f"❌ Redis连接测试失败: {str(e)}")
        return False

def test_session_operations():
    """测试会话操作"""
    try:
        # 测试创建会话
        session_data = {
            "sessionId": "test-session-001",
            "title": "测试会话",
            "description": "这是一个测试会话",
            "consultType": "general",
            "healthInfoUrl": ""
        }
        
        # 创建会话
        result = redis_manager.create_session(session_data)
        if result:
            logger.info("✅ 会话创建测试成功")
        else:
            logger.error("❌ 会话创建测试失败")
            return False
        
        # 测试会话存在检查
        exists = redis_manager.session_exists("test-session-001")
        if exists:
            logger.info("✅ 会话存在检查测试成功")
        else:
            logger.error("❌ 会话存在检查测试失败")
            return False
        
        # 测试获取会话信息
        session_info = redis_manager.get_session("test-session-001")
        if session_info and session_info['sessionId'] == "test-session-001":
            logger.info("✅ 会话信息获取测试成功")
        else:
            logger.error("❌ 会话信息获取测试失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 会话操作测试失败: {str(e)}")
        return False

def test_message_operations():
    """测试消息操作"""
    try:
        # 测试添加消息
        message_data = {
            "messageId": "test-message-001",
            "sessionId": "test-session-001",
            "messageType": 0,
            "content": "这是一条测试消息",
            "sendTime": "2024-01-01T10:00:00",
            "sender": "user"
        }
        
        result = redis_manager.add_message("test-session-001", message_data)
        if result:
            logger.info("✅ 消息添加测试成功")
        else:
            logger.error("❌ 消息添加测试失败")
            return False
        
        # 测试获取消息
        messages_result = redis_manager.get_messages("test-session-001")
        if messages_result and len(messages_result["records"]) > 0:
            logger.info("✅ 消息获取测试成功")
        else:
            logger.error("❌ 消息获取测试失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 消息操作测试失败: {str(e)}")
        return False

def test_task_operations():
    """测试任务操作"""
    try:
        # 测试创建任务
        task_data = {
            "taskId": "test-task-001",
            "sessionId": "test-session-001",
            "messageId": "test-message-001"
        }
        
        result = redis_manager.create_task(task_data)
        if result:
            logger.info("✅ 任务创建测试成功")
        else:
            logger.error("❌ 任务创建测试失败")
            return False
        
        # 测试更新任务状态
        result = redis_manager.update_task("test-task-001", "completed", result={"test": "data"})
        if result:
            logger.info("✅ 任务更新测试成功")
        else:
            logger.error("❌ 任务更新测试失败")
            return False
        
        # 测试获取任务信息
        task_info = redis_manager.get_task("test-task-001")
        if task_info and task_info['status'] == "completed":
            logger.info("✅ 任务信息获取测试成功")
        else:
            logger.error("❌ 任务信息获取测试失败")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 任务操作测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("开始Redis持久化存储测试...")
    
    # 测试连接
    if not test_redis_connection():
        logger.error("Redis连接测试失败，请确保Redis服务器正在运行")
        return
    
    # 测试会话操作
    if not test_session_operations():
        logger.error("会话操作测试失败")
        return
    
    # 测试消息操作
    if not test_message_operations():
        logger.error("消息操作测试失败")
        return
    
    # 测试任务操作
    if not test_task_operations():
        logger.error("任务操作测试失败")
        return
    
    logger.info("🎉 所有Redis持久化存储测试通过！")
    logger.info("✅ 会话ID存储已成功从内存迁移到Redis持久化存储")

if __name__ == "__main__":
    main()
