# 功能说明：实现使用AIFlowy bots API的RAG知识库查询服务，使用fastapi进行发布
# 包含：AIFlowy API调用，Redis会话管理，流式响应处理

import os
import re
import json
import asyncio
import uuid
import time
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from datetime import datetime

# 加载.env文件中的环境变量
load_dotenv()

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import httpx

# 部署REST API相关
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

# 导入Redis管理器
from redis_manager import redis_manager

# 设置日志模版
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AIFlowy API配置相关
AIFLOWY_API_BASE = "http://10.0.0.19:8080"
AIFLOWY_CHAT_ENDPOINT = "/api/v1/aiBot/chat"
AIFLOWY_BOT_ID = "274724831961026560"

# HTTP客户端配置
HTTP_TIMEOUT = 180.0
MAX_RETRIES = 3

# API服务设置相关
PORT = 8013  # 服务访问的端口

# 定义Message类
class Message(BaseModel):
    role: str
    content: str

# 定义ChatCompletionRequest类 请求封装
class ChatCompletionRequest(BaseModel):
    messages: List[Message]
    stream: Optional[bool] = False
    userId: Optional[str] = None
    conversationId: Optional[str] = None

# 定义ChatCompletionResponseChoice类
class ChatCompletionResponseChoice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = None

# 定义ChatCompletionResponse类
class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    choices: List[ChatCompletionResponseChoice]
    system_fingerprint: Optional[str] = None


# 格式化响应，对输入的文本进行段落分隔、添加适当的换行符，以及在代码块中增加标记，以便生成更具可读性的输出
def format_response(response):
    # 使用正则表达式 \n{2, }将输入的response按照两个或更多的连续换行符进行分割。这样可以将文本分割成多个段落，每个段落由连续的非空行组成
    paragraphs = re.split(r'\n{2,}', response)
    # 空列表，用于存储格式化后的段落
    formatted_paragraphs = []
    # 遍历每个段落进行处理
    for para in paragraphs:
        # 检查段落中是否包含代码块标记
        if '```' in para:
            # 将段落按照```分割成多个部分，代码块和普通文本交替出现
            parts = para.split('```')
            for i, part in enumerate(parts):
                # 检查当前部分的索引是否为奇数，奇数部分代表代码块
                if i % 2 == 1:  # 这是代码块
                    # 将代码块部分用换行符和```包围，并去除多余的空白字符
                    parts[i] = f"\n```\n{part.strip()}\n```\n"
            # 将分割后的部分重新组合成一个字符串
            para = ''.join(parts)
        else:
            # 否则，将句子中的句点后面的空格替换为换行符，以便句子之间有明确的分隔
            para = para.replace('. ', '.\n')
        # 将格式化后的段落添加到formatted_paragraphs列表
        # strip()方法用于移除字符串开头和结尾的空白字符（包括空格、制表符 \t、换行符 \n等）
        formatted_paragraphs.append(para.strip())
    # 将所有格式化后的段落用两个换行符连接起来，以形成一个具有清晰段落分隔的文本
    return '\n\n'.join(formatted_paragraphs)


# 构建包含历史对话的完整prompt
def build_conversation_prompt(current_query: str, conversation_history: List[Dict]) -> str:
    """构建包含历史对话的完整prompt"""
    prompt_parts = []
    
    # 如果有历史对话，添加到prompt中
    if conversation_history:
        prompt_parts.append("以下是之前的对话历史：")
        
        # 按时间顺序处理历史消息
        for msg in conversation_history:
            role = "用户" if msg['sender'] == 'user' else "助手"
            prompt_parts.append(f"{role}: {msg['content']}")
        
        prompt_parts.append("")  # 空行分隔
        prompt_parts.append("现在请基于以上对话历史，回答用户的新问题：")
    
    # 添加当前问题
    prompt_parts.append(f"用户: {current_query}")
    prompt_parts.append("助手:")
    
    return "\n".join(prompt_parts)


# 调用AIFlowy API
async def call_aiflowy_api(prompt: str, session_id: str, user_id: str) -> str:
    """调用AIFlowy API，处理SSE响应"""
    logger.info(f"调用AIFlowy API: session_id={session_id}, user_id={user_id}")
    
    # 设置请求头，明确指定接受SSE格式
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.post(
                    f"{AIFLOWY_API_BASE}{AIFLOWY_CHAT_ENDPOINT}",
                    headers=headers,
                    json={
                        "prompt": prompt,
                        "botId": AIFLOWY_BOT_ID,
                        "sessionId": session_id,
                        "isExternalMsg": 1,
                        "tempUserId": user_id
                    }
                )
                response.raise_for_status()
                
                # 处理SSE响应
                full_content = ""
                async for line in response.aiter_lines():
                    line = line.strip()
                    if line.startswith("data:"):
                        try:
                            data_str = line[5:]  # 移除 "data:" 前缀
                            if data_str.strip():
                                data = json.loads(data_str)
                                if "content" in data and data["content"]:
                                    full_content += data["content"]
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析SSE数据: {data_str}")
                
                logger.info(f"AIFlowy API调用成功，回复长度: {len(full_content)}")
                return full_content
                
            except httpx.HTTPStatusError as e:
                logger.error(f"AIFlowy API HTTP错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
            except Exception as e:
                logger.error(f"AIFlowy API调用失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt == MAX_RETRIES - 1:
                    raise
            await asyncio.sleep(2 ** attempt)  # 指数退避


# 构建响应
def build_response(content: str, stream: bool = False):
    """构建标准响应格式"""
    formatted_content = str(format_response(content))
    
    if stream:
        # 流式响应处理
        async def generate_stream():
            chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
            lines = formatted_content.split('\n')
            
            for i, line in enumerate(lines):
                chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": line + '\n'},
                            "finish_reason": None
                        }
                    ]
                }
                yield f"{json.dumps(chunk)}\n"
                await asyncio.sleep(0.1)  # 减少延迟
            
            # 发送结束标记
            final_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"{json.dumps(final_chunk)}\n"
        
        return StreamingResponse(generate_stream(), media_type="text/event-stream")
    else:
        # 非流式响应
        response = ChatCompletionResponse(
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=Message(role="assistant", content=formatted_content),
                    finish_reason="stop"
                )
            ]
        )
        return JSONResponse(content=response.model_dump())


# 定义了一个异步函数 lifespan，它接收一个FastAPI应用实例app作为参数
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    try:
        # 验证Redis连接
        redis_manager.redis_client.ping()
        logger.info("Redis连接成功，服务初始化完成")
        
        # 测试AIFlowy API连接
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                test_response = await client.get(f"{AIFLOWY_API_BASE}/health")
                logger.info("AIFlowy API连接测试成功")
        except Exception as e:
            logger.warning(f"AIFlowy API连接测试失败，但服务将继续启动: {e}")
        
        logger.info("服务启动完成")
    except Exception as e:
        logger.error(f"服务初始化失败: {str(e)}")
        raise

    yield
    # 关闭时执行
    logger.info("正在关闭...")


# lifespan 参数用于在应用程序生命周期的开始和结束时执行一些初始化或清理工作
app = FastAPI(lifespan=lifespan)


# POST请求接口，与AIFlowy bots进行知识问答
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    logger.info(f"收到聊天完成请求: {request.model_dump()}")
    
    try:
        # 获取用户问题
        user_query = request.messages[-1].content
        logger.info(f"用户问题: {user_query}")
        
        # 处理会话ID和用户ID
        conversation_id = request.conversationId or str(uuid.uuid4())
        user_id = request.userId or "default_user"
        
        # 只有当conversationId为空时才生成新的UUID
        # 如果用户提供了conversationId（即使不是UUID格式），也应该使用它
        if not request.conversationId:
            # 确保生成的conversation_id是有效的UUID格式
            try:
                uuid.UUID(conversation_id)
            except ValueError:
                conversation_id = str(uuid.uuid4())
        
        # 检查会话是否存在，不存在则创建
        if not redis_manager.session_exists(conversation_id):
            session_data = {
                "sessionId": conversation_id,
                "title": user_query[:50] + "..." if len(user_query) > 50 else user_query,
                "description": "AI健康咨询会话",
                "consultType": "health_advice"
            }
            if redis_manager.create_session(session_data):
                logger.info(f"创建新会话: {conversation_id}")
            else:
                logger.warning(f"会话创建失败，但继续处理: {conversation_id}")
        
        # 映射ID格式给AIFlowy
        aiflowy_session_id = f"external_session_{conversation_id}"
        aiflowy_user_id = f"external_user_{user_id}"
        
        # 保存用户消息到Redis
        user_message = {
            "messageId": str(uuid.uuid4()),
            "messageType": 1,  # 用户消息
            "content": user_query,
            "sendTime": datetime.now().isoformat(),
            "sender": "user"
        }
        redis_manager.add_message(conversation_id, user_message)
        
        # 获取历史对话（包含刚保存的用户消息）
        history_messages = redis_manager.get_messages(conversation_id, page_size=50)
        conversation_history = []
        
        if history_messages and history_messages.get('records'):
            # Redis返回的是按时间倒序排列的（最新的在前），我们需要重新按时间正序排列
            sorted_records = sorted(history_messages['records'], 
                                 key=lambda x: x.get('sendTime', ''))
            conversation_history = sorted_records
            
            # 由于我们刚保存了当前用户消息，它应该是最后一条（时间最晚的）
            # 我们需要排除它，避免在历史中重复
            if conversation_history:
                # 找到刚保存的用户消息并排除它
                # 通过比较消息内容和时间来识别当前消息
                current_msg_index = -1
                for i, msg in enumerate(conversation_history):
                    if (msg.get('content') == user_query and 
                        msg.get('sender') == 'user' and
                        msg.get('sendTime', '') == user_message['sendTime']):
                        current_msg_index = i
                        break
                
                if current_msg_index != -1:
                    conversation_history.pop(current_msg_index)
                    logger.info(f"排除了当前用户消息，索引: {current_msg_index}")
        
        # 构建包含历史对话的完整prompt
        full_prompt = build_conversation_prompt(user_query, conversation_history)
        logger.info(f"构建的完整prompt长度: {len(full_prompt)}")
        logger.info(f"完整prompt内容: {full_prompt[:500]}...")
        
        # 打印历史消息数量用于调试
        logger.info(f"历史消息数量: {len(conversation_history)}")
        if conversation_history:
            logger.info(f"第一条历史消息: {conversation_history[0].get('content', '')[:50]}...")
            logger.info(f"最后一条历史消息: {conversation_history[-1].get('content', '')[:50]}...")
        
        # 调用AIFlowy API
        logger.info("开始调用AIFlowy API")
        response_content = await call_aiflowy_api(full_prompt, aiflowy_session_id, aiflowy_user_id)
        
        # 检查回复内容
        if not response_content.strip():
            logger.warning("AIFlowy返回空回复")
            response_content = "抱歉，服务暂时不可用，请稍后重试。"
        
        logger.info(f"AIFlowy回复内容: {response_content[:200]}...")
        
        # 保存AI回复到Redis
        assistant_message = {
            "messageId": str(uuid.uuid4()),
            "messageType": 2,  # AI回复
            "content": response_content,
            "sendTime": datetime.now().isoformat(),
            "sender": "assistant"
        }
        redis_manager.add_message(conversation_id, assistant_message)
        
        # 返回响应
        return build_response(response_content, request.stream)
        
    except Exception as e:
        logger.error(f"处理聊天完成时出错: {str(e)}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="服务暂时不可用，请稍后重试")


# 健康检查接口
@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        # 检查Redis连接
        redis_manager.redis_client.ping()
        
        # 检查AIFlowy API连接
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AIFLOWY_API_BASE}/health")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": "connected",
                "aiflowy": "connected"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


if __name__ == "__main__":
    logger.info(f"在端口 {PORT} 上启动服务器")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
