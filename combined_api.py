# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import aiohttp
import json
import logging
import asyncio
import requests
from http import HTTPStatus
from dashscope import Application
from redis_manager import redis_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="XinMai AI API", description="整合了会话管理和OSS文件处理的AI API")

# 阿里云百炼配置
DASHSCOPE_API_KEY = "sk-8ac6ce8ab2f24126b166604f97f0af81"
BAILIAN_APP_ID = "55a12bae78c94eedb494b301787bc833"

# ==================== 数据模型定义 ====================

class CreateAiSessionDTO(BaseModel):
    sessionId: str = Field(..., description="前端会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    description: Optional[str] = Field(None, description="会话描述")
    consultType: Optional[str] = Field(None, description="咨询类型")
    healthInfoUrl: Optional[str] = Field(None, description="健康信息URL")

class SendMessageDTO(BaseModel):
    sessionId: str = Field(..., description="会话ID")
    messageId: str = Field(..., description="消息ID")
    content: str = Field(..., description="消息内容")
    messageType: int = Field(0, description="消息类型(0文本,1图片,2文件,3图文,4语音),第一版只有0")
    sendTime: Optional[str] = Field(None, description="发送时间")
    callbackUrl: Optional[str] = Field(None, description="回调URL，用于接收AI回复通知")

    @field_validator('messageType')
    def message_type_must_be_valid(cls, v):
        if v not in [0, 1, 2, 3, 4]:
            raise ValueError('消息类型只能是0（文本）、1（图片）、2（文件）、3（图文）、4（语音）')
        return v

class QueryMessagePageDTO(BaseModel):
    sessionId: str = Field(..., description="会话ID")
    startMessageId: Optional[str] = Field(None, description="开始消息id,如果为空则倒序往前查")
    pageNum: int = Field(..., description="页码")
    pageSize: int = Field(..., description="每页条数")

    @field_validator('pageNum')
    def page_num_must_be_positive(cls, v):
        if v < 1:
            raise ValueError('页码必须大于0')
        return v

    @field_validator('pageSize')
    def page_size_must_be_valid(cls, v):
        if not (1 <= v <= 100):
            raise ValueError('每页数量必须在1-100之间')
        return v

class SubmitTaskRequest(BaseModel):
    signed_oss_url: str = Field(..., description="带签名的OSS文件URL")

# ==================== 工具函数 ====================

def api_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "data": data
    }

def get_signed_oss_content(signed_url: str) -> Optional[str]:
    """从带签名的OSS URL获取文件内容"""
    try:
        response = requests.get(
            signed_url,
            timeout=15,
            headers={"User-Agent": "FastAPI-OSS-Client/1.0"}
        )
        if response.status_code != HTTPStatus.OK:
            logger.error(f"OSS访问失败，状态码: {response.status_code}, 响应: {response.text}")
            return None
        
        content = response.content.decode(response.apparent_encoding or 'utf-8')
        logger.info(f"成功获取OSS文件内容，长度: {len(content)}字符")
        return content
        
    except requests.exceptions.Timeout:
        logger.error("访问OSS超时")
        return None
    except requests.exceptions.SSLError:
        logger.error("OSS SSL证书验证失败")
        return None
    except Exception as e:
        logger.error(f"获取OSS内容异常: {str(e)}")
        return None

async def send_webhook_callback(callback_url: str, callback_data: Dict[str, Any]):
    """发送Webhook回调通知"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                callback_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(callback_data),
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    logger.info(f"Webhook回调成功: {callback_url}")
                else:
                    logger.warning(f"Webhook回调失败: {response.status} - {await response.text()}")
    except Exception as e:
        logger.error(f"Webhook回调异常: {str(e)}")

# ==================== 后台处理函数 ====================

async def process_message_async(sessionId: str, dto: SendMessageDTO, task_id: str):
    """处理用户消息的异步任务"""
    try:
        ai_message_id = str(uuid.uuid4())[:8]
        llm_url = "http://localhost:8013/v1/chat/completions"
        
        async with aiohttp.ClientSession() as session:
            llm_data = {
                "messages": [{"role": "user", "content": dto.content}],
                "stream": False,
                "userId": dto.sessionId,
                "conversationId": dto.sessionId
            }
            
            try:
                async with session.post(
                    llm_url, 
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(llm_data)
                ) as response:
                    response.raise_for_status()
                    llm_response = await response.json()
                    ai_content = llm_response['choices'][0]['message']['content']
                    
            except aiohttp.ClientError as e:
                ai_content = f"抱歉，AI服务暂时不可用。错误信息: {str(e)}"
            except (KeyError, json.JSONDecodeError) as e:
                ai_content = f"抱歉，AI响应解析错误。错误信息: {str(e)}"
        
        # 创建AI消息并存储到Redis
        ai_message = {
            "messageId": ai_message_id,
            "sessionId": dto.sessionId,
            "messageType": 0,
            "content": ai_content,
            "sendTime": datetime.now().isoformat(),
            "sender": "ai"
        }
        redis_manager.add_message(dto.sessionId, ai_message)
        
        # 更新任务状态
        redis_manager.update_task(
            task_id, 
            "completed", 
            result={
                "userMessageId": dto.messageId,
                "aiMessage": ai_message
            }
        )
        
        # 如果有回调URL，发送Webhook回调
        if dto.callbackUrl:
            callback_data = {
                "sessionId": dto.sessionId,
                "messageId": ai_message_id,
                "messageType": 0,
                "content": ai_content
            }
            asyncio.create_task(send_webhook_callback(dto.callbackUrl, callback_data))
            logger.info(f"已发送Webhook回调: {dto.callbackUrl}")
        
    except Exception as e:
        redis_manager.update_task(task_id, "failed", error=str(e))
        if dto.callbackUrl:
            error_callback_data = {
                "sessionId": dto.sessionId,
                "messageId": str(uuid.uuid4())[:8],
                "messageType": 0,
                "content": f"AI处理失败: {str(e)}"
            }
            asyncio.create_task(send_webhook_callback(dto.callbackUrl, error_callback_data))

async def process_oss_data_async(signed_oss_url: str, task_id: str):
    """处理OSS数据的异步任务"""
    try:
        # 更新任务状态为处理中
        redis_manager.update_task(task_id, "processing", progress="开始处理OSS数据")
        
        # 获取OSS内容
        oss_content = await asyncio.get_event_loop().run_in_executor(
            None, get_signed_oss_content, signed_oss_url
        )
        
        if not oss_content:
            redis_manager.update_task(task_id, "failed", error="无法获取OSS文件内容")
            return
        
        redis_manager.update_task(task_id, "processing", progress="OSS内容获取成功，开始调用智能体")
        
        # 调用阿里云百炼智能体
        try:
            agent_response = await asyncio.get_event_loop().run_in_executor(
                None, Application.call,
                DASHSCOPE_API_KEY,
                BAILIAN_APP_ID,
                f"请分析处理以下数据并给出结果：\n{oss_content}"
            )
            
            if agent_response.status_code != HTTPStatus.OK:
                redis_manager.update_task(
                    task_id, "failed", 
                    error=f"智能体处理失败: {agent_response.message}"
                )
                return
            
            # 任务成功完成
            redis_manager.update_task(
                task_id, "completed",
                result={
                    "success": True,
                    "message": "OSS数据处理成功",
                    "request_id": agent_response.request_id,
                    "oss_url": signed_oss_url,
                    "result": agent_response.output.text
                }
            )
            
        except Exception as e:
            redis_manager.update_task(task_id, "failed", error=f"智能体调用异常: {str(e)}")
            
    except Exception as e:
        redis_manager.update_task(task_id, "failed", error=f"处理过程异常: {str(e)}")

# ==================== API接口 ====================

# 1. 创建/发起新的会话接口
@app.post('/api/ai/sessions')
async def create_session(dto: CreateAiSessionDTO):
    try:
        if redis_manager.session_exists(dto.sessionId):
            return JSONResponse(
                content=api_response(False, "会话已存在"),
                status_code=400
            )
        
        session_data = {
            "sessionId": dto.sessionId,
            "title": dto.title or "",
            "description": dto.description or "",
            "consultType": dto.consultType or "",
            "healthInfoUrl": dto.healthInfoUrl or ""
        }
        
        if redis_manager.create_session(session_data):
            return JSONResponse(
                content=api_response(
                    True, 
                    "会话创建成功",
                    {
                        "sessionId": dto.sessionId,
                        "createTime": datetime.now().isoformat()
                    }
                ),
                status_code=201
            )
        else:
            return JSONResponse(
                content=api_response(False, "会话创建失败"),
                status_code=500
            )
    
    except Exception as e:
        logger.error(f"创建会话异常: {str(e)}")
        return JSONResponse(
            content=api_response(False, str(e)),
            status_code=400
        )

# 2. 发送消息接口
@app.post('/api/ai/sessions/{sessionId}/messages')
async def send_message(sessionId: str, dto: SendMessageDTO, background_tasks: BackgroundTasks):
    try:
        if dto.sessionId != sessionId:
            return JSONResponse(
                content=api_response(False, "路径会话ID与请求体不一致"),
                status_code=400
            )
        
        if not redis_manager.session_exists(dto.sessionId):
            return JSONResponse(
                content=api_response(False, "会话不存在"),
                status_code=404
            )
        
        sendTime = dto.sendTime or datetime.now().isoformat()
        
        user_message = {
            "messageId": dto.messageId,
            "sessionId": dto.sessionId,
            "messageType": dto.messageType,
            "content": dto.content,
            "sendTime": sendTime,
            "sender": "user"
        }
        redis_manager.add_message(dto.sessionId, user_message)
        
        task_id = str(uuid.uuid4())
        task_data = {
            "taskId": task_id,
            "status": "processing",
            "sessionId": sessionId,
            "messageId": dto.messageId,
            "createdAt": datetime.now().isoformat()
        }
        redis_manager.create_task(task_data)
        
        background_tasks.add_task(process_message_async, sessionId, dto, task_id)
        
        return JSONResponse(
            content=api_response(
                True,
                "消息已接收，正在处理中",
                {
                    "taskId": task_id,
                    "status": "processing",
                    "userMessageId": dto.messageId
                }
            ),
            status_code=202
        )
    
    except Exception as e:
        return JSONResponse(
            content=api_response(False, str(e)),
            status_code=400
        )

# 3. 分页查询消息接口
@app.get('/api/ai/sessions/{sessionId}/messages')
async def query_messages(
    sessionId: str,
    startMessageId: Optional[str] = None,
    pageNum: int = 1,
    pageSize: int = 10
):
    try:
        if not redis_manager.session_exists(sessionId):
            return JSONResponse(
                content=api_response(False, "会话不存在"),
                status_code=404
            )
        
        messages_result = redis_manager.get_messages(sessionId, page_num=pageNum, page_size=pageSize)
        session_messages = messages_result["records"]
        
        if startMessageId:
            start_index = next(
                (i for i, msg in enumerate(session_messages) 
                 if msg["messageId"] == startMessageId),
                None
            )
            if start_index is not None:
                session_messages = session_messages[start_index+1:]
        
        total = len(session_messages)
        start = (pageNum - 1) * pageSize
        end = start + pageSize
        page_messages = session_messages[start:end]
        
        response_data = {
            "total": total,
            "pageSize": pageSize,
            "current": pageNum,
            "records": [
                {k: v for k, v in msg.items() if k != "sender"} 
                for msg in page_messages
            ]
        }
        
        return JSONResponse(
            content=api_response(True, "查询成功", response_data),
            status_code=200
        )
    
    except Exception as e:
        return JSONResponse(
            content=api_response(False, str(e)),
            status_code=400
        )

# 4. 结束会话接口
@app.post('/api/ai/sessions/{sessionId}/end')
async def end_session(sessionId: str):
    try:
        if not redis_manager.session_exists(sessionId):
            return JSONResponse(
                content=api_response(False, "会话不存在"),
                status_code=404
            )
        
        end_time = datetime.now().isoformat()
        if redis_manager.end_session(sessionId, end_time):
            return JSONResponse(
                content=api_response(
                    True, 
                    "会话已结束",
                    {"sessionId": sessionId, "endTime": end_time}
                ),
                status_code=200
            )
        else:
            return JSONResponse(
                content=api_response(False, "结束会话失败"),
                status_code=500
            )
    
    except Exception as e:
        logger.error(f"结束会话异常: {str(e)}")
        return JSONResponse(
            content=api_response(False, str(e)),
            status_code=400
        )

# 5. 提交OSS处理任务接口（原agent_api.py功能）
@app.post('/api/ai/oss-tasks')
async def submit_oss_task(request: SubmitTaskRequest, background_tasks: BackgroundTasks):
    """提交OSS数据处理任务"""
    try:
        signed_oss_url = request.signed_oss_url
        logger.info(f"收到OSS任务提交请求，URL: {signed_oss_url}")
        
        task_id = str(uuid.uuid4())
        task_data = {
            "taskId": task_id,
            "status": "pending",
            "type": "oss_processing",
            "oss_url": signed_oss_url,
            "createdAt": datetime.now().isoformat()
        }
        redis_manager.create_task(task_data)
        
        # 添加后台任务
        background_tasks.add_task(process_oss_data_async, signed_oss_url, task_id)
        
        return JSONResponse(
            content=api_response(
                True,
                "OSS任务已提交，正在后台处理",
                {
                    "taskId": task_id,
                    "status": "pending",
                    "oss_url": signed_oss_url
                }
            ),
            status_code=202
        )
    
    except Exception as e:
        logger.error(f"提交OSS任务异常: {str(e)}")
        return JSONResponse(
            content=api_response(False, f"任务提交失败: {str(e)}"),
            status_code=500
        )

# 6. 查询任务状态接口（统一查询所有类型的任务）
@app.get('/api/ai/tasks/{taskId}')
async def get_task_status(taskId: str):
    try:
        task_info = redis_manager.get_task(taskId)
        if not task_info:
            return JSONResponse(
                content=api_response(False, "任务不存在"),
                status_code=404
            )
        
        if task_info["status"] == "completed":
            return JSONResponse(
                content=api_response(
                    True,
                    "任务已完成",
                    {
                        "taskId": taskId,
                        "status": "completed",
                        "result": task_info.get("result"),
                        "completed_at": task_info.get("completedAt")
                    }
                ),
                status_code=200
            )
        elif task_info["status"] == "failed":
            return JSONResponse(
                content=api_response(
                    False,
                    "任务处理失败",
                    {
                        "taskId": taskId,
                        "status": "failed",
                        "error": task_info.get("error"),
                        "failed_at": task_info.get("failedAt")
                    }
                ),
                status_code=200
            )
        else:
            return JSONResponse(
                content=api_response(
                    True,
                    "任务处理中",
                    {
                        "taskId": taskId,
                        "status": task_info["status"],
                        "progress": task_info.get("progress"),
                        "created_at": task_info.get("createdAt")
                    }
                ),
                status_code=200
            )
    
    except Exception as e:
        logger.error(f"查询任务状态异常: {str(e)}")
        return JSONResponse(
            content=api_response(False, str(e)),
            status_code=400
        )

# 7. 健康检查接口
@app.get('/health')
async def health_check():
    """健康检查接口"""
    return JSONResponse(
        content=api_response(True, "服务运行正常", {
            "service": "XinMai AI API",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        })
    )

# 8. API文档重定向
@app.get('/')
async def root():
    """API根路径，重定向到文档"""
    return JSONResponse(
        content=api_response(True, "XinMai AI API服务运行中", {
            "docs_url": "/docs",
            "redoc_url": "/redoc"
        })
    )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=5000)
