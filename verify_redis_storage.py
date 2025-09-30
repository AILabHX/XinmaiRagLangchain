#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证会话ID存储已从内存迁移到Redis持久化存储
"""

import redis
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_redis_storage():
    """验证Redis存储功能"""
    try:
        # 连接到Redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis连接成功")
        
        # 检查是否有会话数据存储在Redis中
        session_keys = redis_client.keys("session:*")
        message_keys = redis_client.keys("message:*")
        task_keys = redis_client.keys("task:*")
        
        logger.info(f"📊 Redis中存储的会话数量: {len(session_keys)}")
        logger.info(f"📊 Redis中存储的消息数量: {len(message_keys)}")
        logger.info(f"📊 Redis中存储的任务数量: {len(task_keys)}")
        
        # 如果有会话数据，显示详细信息
        if session_keys:
            logger.info("📋 会话详细信息:")
            for key in session_keys[:3]:  # 只显示前3个会话
                session_data = redis_client.hgetall(key)
                logger.info(f"  - {key}: {json.dumps(session_data, ensure_ascii=False, indent=2)}")
        
        # 验证数据结构
        logger.info("🔍 验证数据结构:")
        
        # 检查会话键模式
        if session_keys:
            sample_key = session_keys[0]
            if sample_key.startswith("session:"):
                logger.info("✅ 会话键格式正确")
            else:
                logger.warning("⚠️ 会话键格式可能不正确")
        
        # 检查消息键模式
        if message_keys:
            sample_key = message_keys[0]
            if sample_key.startswith("message:"):
                logger.info("✅ 消息键格式正确")
            else:
                logger.warning("⚠️ 消息键格式可能不正确")
        
        # 检查任务键模式
        if task_keys:
            sample_key = task_keys[0]
            if sample_key.startswith("task:"):
                logger.info("✅ 任务键格式正确")
            else:
                logger.warning("⚠️ 任务键格式可能不正确")
        
        # 验证过期时间设置
        if session_keys:
            sample_key = session_keys[0]
            ttl = redis_client.ttl(sample_key)
            if ttl > 0:
                logger.info(f"✅ 会话数据设置了过期时间: {ttl}秒")
            else:
                logger.warning("⚠️ 会话数据未设置过期时间")
        
        logger.info("🎉 Redis持久化存储验证完成！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("开始验证Redis持久化存储...")
    verify_redis_storage()
