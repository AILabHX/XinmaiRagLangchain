#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云Redis连接测试脚本
专门用于测试阿里云Redis服务的连接和功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from redis_manager import RedisManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_aliyun_redis_connection():
    """测试阿里云Redis连接"""
    try:
        # 使用阿里云Redis配置创建管理器
        aliyun_redis_manager = RedisManager(
            host='r-2vcvlqn3xxvgrh75hcpd.redis.cn-chengdu.rds.aliyuncs.com',
            port=6379,
            db=3,
            password='5IevEcX3C7BhLNZR'
        )
        
        # 测试连接
        aliyun_redis_manager.redis_client.ping()
        logger.info("✅ 阿里云Redis连接测试成功")
        return aliyun_redis_manager
        
    except Exception as e:
        logger.error(f"❌ 阿里云Redis连接测试失败: {str(e)}")
        return None

def test_aliyun_redis_operations(redis_manager):
    """测试阿里云Redis基本操作"""
    try:
        # 测试键值操作
        test_key = "test:aliyun:connection"
        test_value = "阿里云Redis连接测试成功"
        
        # 设置值
        redis_manager.redis_client.set(test_key, test_value)
        
        # 获取值
        retrieved_value = redis_manager.redis_client.get(test_key)
        
        if retrieved_value == test_value:
            logger.info("✅ 阿里云Redis键值操作测试成功")
        else:
            logger.error("❌ 阿里云Redis键值操作测试失败")
            return False
        
        # 清理测试数据
        redis_manager.redis_client.delete(test_key)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 阿里云Redis操作测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    logger.info("开始阿里云Redis连接测试...")
    
    # 测试阿里云Redis连接
    aliyun_redis_manager = test_aliyun_redis_connection()
    if not aliyun_redis_manager:
        logger.error("阿里云Redis连接测试失败，请检查网络连接和配置")
        return
    
    # 测试阿里云Redis基本操作
    if not test_aliyun_redis_operations(aliyun_redis_manager):
        logger.error("阿里云Redis操作测试失败")
        return
    
    logger.info("🎉 阿里云Redis连接和操作测试全部通过！")
    logger.info("✅ 阿里云Redis服务配置正确，可以正常使用")

if __name__ == "__main__":
    main()
