# -*- coding: utf-8 -*-
import redis
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self, host: str = None, port: int = None, db: int = None, password: str = None):
        """初始化Redis连接，支持环境变量配置"""
        try:
            # 从环境变量获取配置，如果没有则使用默认值
            redis_host = host or os.getenv('REDIS_HOST', 'localhost')
            redis_port = port or int(os.getenv('REDIS_PORT', '6379'))
            redis_db = db or int(os.getenv('REDIS_DB', '0'))
            redis_password = password or os.getenv('REDIS_PASSWORD', '')
            
            logger.info(f"正在连接Redis: {redis_host}:{redis_port}, DB: {redis_db}")
            
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password if redis_password else None,
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True
            )
            # 测试连接
            self.redis_client.ping()
            logger.info(f"Redis连接成功: {redis_host}:{redis_port}, DB: {redis_db}")
        except Exception as e:
            logger.error(f"Redis连接失败: {str(e)}")
            raise
    
    def _get_session_key(self, session_id: str) -> str:
        """获取会话存储键名"""
        return f"session:{session_id}"
    
    def _get_messages_key(self, session_id: str) -> str:
        """获取消息列表键名"""
        return f"messages:{session_id}"
    
    def _get_message_key(self, session_id: str, message_id: str) -> str:
        """获取单个消息存储键名"""
        return f"message:{session_id}:{message_id}"
    
    def _get_task_key(self, task_id: str) -> str:
        """获取任务存储键名"""
        return f"task:{task_id}"
    
    def create_session(self, session_data: Dict[str, Any]) -> bool:
        """创建新会话"""
        try:
            session_id = session_data['sessionId']
            session_key = self._get_session_key(session_id)
            
            # 检查会话是否已存在
            if self.redis_client.exists(session_key):
                logger.warning(f"会话已存在: {session_id}")
                return False
            
            # 创建会话数据
            session_info = {
                'sessionId': session_id,
                'title': session_data.get('title', ''),
                'description': session_data.get('description', ''),
                'consultType': session_data.get('consultType', ''),
                'healthInfoUrl': session_data.get('healthInfoUrl', ''),
                'status': 'active',
                'createTime': datetime.now().isoformat(),
                'lastActivityTime': datetime.now().isoformat()
            }
            
            # 存储会话信息（设置24小时过期时间）
            # 使用hmset替代hset mapping，兼容更多Redis版本
            self.redis_client.hmset(session_key, session_info)
            # self.redis_client.expire(session_key, 24 * 60 * 60)  # 24小时 - 注释掉过期时间
            
            # 创建空的消息列表
            messages_key = self._get_messages_key(session_id)
            # self.redis_client.expire(messages_key, 24 * 60 * 60)  # 24小时 - 注释掉过期时间
            
            logger.info(f"会话创建成功: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建会话失败: {str(e)}")
            return False
    
    def session_exists(self, session_id: str) -> bool:
        """检查会话是否存在"""
        try:
            session_key = self._get_session_key(session_id)
            return self.redis_client.exists(session_key) > 0
        except Exception as e:
            logger.error(f"检查会话存在失败: {str(e)}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        try:
            session_key = self._get_session_key(session_id)
            session_data = self.redis_client.hgetall(session_key)
            
            if session_data:
                return session_data
            return None
            
        except Exception as e:
            logger.error(f"获取会话失败: {str(e)}")
            return None
    
    def add_message(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """添加消息"""
        try:
            message_id = message_data['messageId']
            
            # 检查会话是否存在
            if not self.session_exists(session_id):
                logger.error(f"会话不存在: {session_id}")
                return False
            
            # 存储消息详情
            message_key = self._get_message_key(session_id, message_id)
            message_detail = {
                'messageId': message_id,
                'sessionId': session_id,
                'messageType': str(message_data['messageType']),
                'content': message_data['content'],
                'sendTime': message_data['sendTime'],
                'sender': message_data['sender']
            }
            
            self.redis_client.hmset(message_key, message_detail)
            # self.redis_client.expire(message_key, 24 * 60 * 60)  # 24小时 - 注释掉过期时间
            
            # 将消息ID添加到会话的消息列表中（按时间排序）
            messages_key = self._get_messages_key(session_id)
            send_time = datetime.fromisoformat(message_data['sendTime']).timestamp()
            
            # 使用有序集合存储消息，按发送时间排序
            self.redis_client.zadd(messages_key, {message_id: send_time})
            # self.redis_client.expire(messages_key, 24 * 60 * 60)  # 24小时 - 注释掉过期时间
            
            # 更新会话的最后活动时间
            session_key = self._get_session_key(session_id)
            self.redis_client.hset(session_key, 'lastActivityTime', datetime.now().isoformat())
            
            logger.info(f"消息添加成功: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加消息失败: {str(e)}")
            return False
    
    def get_messages(self, session_id: str, start_message_id: Optional[str] = None, 
                    page_num: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """分页获取消息"""
        try:
            if not self.session_exists(session_id):
                return {"total": 0, "pageSize": page_size, "current": page_num, "records": []}
            
            messages_key = self._get_messages_key(session_id)
            
            # 获取消息总数
            total = self.redis_client.zcard(messages_key)
            
            # 计算分页
            start_index = (page_num - 1) * page_size
            end_index = start_index + page_size - 1
            
            # 获取当前页的消息ID（按时间倒序，最新的在前）
            message_ids = self.redis_client.zrevrange(messages_key, start_index, end_index)
            
            # 获取消息详情
            messages = []
            for msg_id in message_ids:
                message_key = self._get_message_key(session_id, msg_id)
                message_data = self.redis_client.hgetall(message_key)
                if message_data:
                    messages.append(message_data)
            
            return {
                "total": total,
                "pageSize": page_size,
                "current": page_num,
                "records": messages
            }
            
        except Exception as e:
            logger.error(f"获取消息失败: {str(e)}")
            return {"total": 0, "pageSize": page_size, "current": page_num, "records": []}
    
    def end_session(self, session_id: str, end_time: str = None) -> bool:
        """结束会话"""
        try:
            session_key = self._get_session_key(session_id)
            
            if not self.redis_client.exists(session_key):
                logger.error(f"会话不存在: {session_id}")
                return False
            
            # 更新会话状态
            self.redis_client.hset(session_key, 'status', 'ended')
            self.redis_client.hset(session_key, 'endTime', end_time or datetime.now().isoformat())
            
            logger.info(f"会话结束成功: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"结束会话失败: {str(e)}")
            return False
    
    def create_task(self, task_data: Dict[str, Any]) -> bool:
        """创建任务"""
        try:
            task_id = task_data['taskId']
            task_key = self._get_task_key(task_id)
            
            task_info = {
                'taskId': task_id,
                'sessionId': task_data['sessionId'],
                'messageId': task_data['messageId'],
                'status': 'processing',
                'createdAt': datetime.now().isoformat()
            }
            
            # 存储任务信息（设置1小时过期时间）
            self.redis_client.hmset(task_key, task_info)
            # self.redis_client.expire(task_key, 60 * 60)  # 1小时 - 注释掉过期时间
            
            logger.info(f"任务创建成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            return False
    
    def update_task(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None, 
                   error: Optional[str] = None) -> bool:
        """更新任务状态"""
        try:
            task_key = self._get_task_key(task_id)
            
            if not self.redis_client.exists(task_key):
                logger.error(f"任务不存在: {task_id}")
                return False
            
            updates = {'status': status}
            
            if status == 'completed':
                updates['completedAt'] = datetime.now().isoformat()
                if result:
                    updates['result'] = json.dumps(result, ensure_ascii=False)
            elif status == 'failed':
                updates['failedAt'] = datetime.now().isoformat()
                if error:
                    updates['error'] = error
            
            self.redis_client.hmset(task_key, updates)
            
            logger.info(f"任务更新成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务失败: {str(e)}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        try:
            task_key = self._get_task_key(task_id)
            task_data = self.redis_client.hgetall(task_key)
            
            if task_data:
                # 解析JSON字段
                if 'result' in task_data and task_data['result']:
                    try:
                        task_data['result'] = json.loads(task_data['result'])
                    except json.JSONDecodeError:
                        task_data['result'] = None
                return task_data
            return None
            
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}")
            return None

# 全局Redis管理器实例
redis_manager = RedisManager()
