# 功能说明：使用dify chatflow API构建RAG知识库查询应用，使用fastapi进行发布
# 简化版本：移除LangChain依赖，直接调用dify API

import os
import re
import json
import asyncio
import uuid
import time
import logging
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

# 设置日志模版
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# dify相关配置
DIFY_API_BASE = "http://192.168.96.1/v1"  # dify服务地址
DIFY_API_KEY = os.getenv("DIFY_API_KEY")  # dify API密钥
DIFY_CHAT_ENDPOINT = "/chat-messages"

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
    user: Optional[str] = None  # 兼容user字段
    conversation_id: Optional[str] = None  # 兼容conversation_id字段

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


async def call_dify_api(query: str, conversation_id: str = None, user_id: str = None, stream: bool = False):
    """调用dify chatflow API，让dify处理所有RAG功能"""
    if not DIFY_API_KEY:
        raise HTTPException(status_code=500, detail="DIFY_API_KEY未配置")
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 验证conversation_id是否为有效的UUID格式
    if conversation_id and conversation_id.strip():
        try:
            uuid.UUID(conversation_id)
        except ValueError:
            # 如果不是有效的UUID，设置为空字符串
            conversation_id = ""
    
    payload = {
        "inputs": {},  # 不需要传递context，dify会自己检索知识库
        "query": query,
        "response_mode": "streaming" if stream else "blocking",
        "conversation_id": conversation_id or "",
        "user": user_id or "default_user"
    }
    
    logger.info(f"调用dify API，请求参数: {payload}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DIFY_API_BASE}{DIFY_CHAT_ENDPOINT}",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            # 记录响应状态和内容
            logger.info(f"dify API响应状态码: {response.status_code}")
            logger.info(f"dify API响应头: {dict(response.headers)}")
            logger.info(f"dify API原始响应内容: {response.text}")
            
            response.raise_for_status()
            
            # 检查响应内容是否为空
            if not response.text or response.text.strip() == "":
                logger.error("dify API返回空响应")
                raise HTTPException(status_code=500, detail="dify API返回空响应")
            
            # 改进JSON解析，处理可能的响应格式问题
            try:
                result = response.json()
                logger.info(f"dify API JSON解析成功: {result}")
                return result
            except json.JSONDecodeError as json_error:
                logger.error(f"dify API响应JSON解析失败: {str(json_error)}")
                logger.error(f"原始响应内容: {repr(response.text)}")
                raise HTTPException(status_code=500, detail=f"dify API响应格式错误: {str(json_error)}")
                
    except httpx.TimeoutException:
        logger.error("dify API请求超时")
        raise HTTPException(status_code=504, detail="dify API请求超时")
    except httpx.HTTPStatusError as e:
        logger.error(f"dify API HTTP错误: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"dify API错误: {e.response.text}")
    except Exception as e:
        logger.error(f"调用dify API时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调用dify API失败: {str(e)}")


async def generate_dify_stream(dify_response):
    """处理dify的流式响应"""
    chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
    
    # 从dify响应中获取回答内容
    answer = dify_response.get("answer", "")
    lines = answer.split('\n')
    
    for i, line in enumerate(lines):
        if line.strip():  # 只发送非空行
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
            await asyncio.sleep(0.05)  # 控制流式响应速度
    
    # 结束标记
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


# 定义了一个异步函数 lifespan，它接收一个FastAPI应用实例app作为参数。这个函数将管理应用的生命周期，包括启动和关闭时的操作
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("正在初始化服务...")
    
    # 验证dify配置
    if not DIFY_API_KEY or DIFY_API_KEY == "your_dify_api_key_here":
        logger.error("DIFY_API_KEY未配置或为默认值，请在.env文件中设置正确的DIFY_API_KEY")
        raise Exception("DIFY_API_KEY未正确配置")
    
    logger.info("服务初始化完成")
    
    # yield 关键字将控制权交还给FastAPI框架，使应用开始运行
    yield
    
    # 关闭时执行
    logger.info("正在关闭...")


# lifespan 参数用于在应用程序生命周期的开始和结束时执行一些初始化或清理工作
app = FastAPI(lifespan=lifespan)


# POST请求接口，与dify chatflow进行知识问答
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    logger.info(f"前端原始请求: {request.model_dump()}")
    
    try:
        logger.info(f"收到聊天完成请求")
        query_prompt = request.messages[-1].content
        logger.info(f"用户问题是: {query_prompt}")
        
        # 处理不同的参数名称格式，兼容多种请求格式
        user_id = request.userId or request.user or "default_user"
        conversation_id = request.conversationId or request.conversation_id or ""
        
        logger.info(f"处理后的参数 - user_id: {user_id}, conversation_id: {conversation_id}")
        
        # 直接调用dify API，不再进行本地向量检索
        logger.info(f"开始调用 dify API...")
        dify_response = await call_dify_api(
            query=query_prompt,
            conversation_id=conversation_id,
            user_id=user_id,
            stream=request.stream
        )
        logger.info(f"dify API 调用成功")
        
        # 处理响应
        if request.stream:
            return StreamingResponse(generate_dify_stream(dify_response), media_type="text/event-stream")
        else:
            answer = dify_response.get("answer", "")
            formatted_response = format_response(answer)
            
            response = ChatCompletionResponse(
                choices=[
                    ChatCompletionResponseChoice(
                        index=0,
                        message=Message(role="assistant", content=formatted_response),
                        finish_reason="stop"
                    )
                ]
            )
            logger.info(f"发送响应内容")
            return JSONResponse(content=response.model_dump())
            
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"处理聊天完成时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "dify-chatflow-api"}


if __name__ == "__main__":
    logger.info(f"在端口 {PORT} 上启动服务器")
    # uvicorn是一个用于运行ASGI应用的轻量级、超快速的ASGI服务器实现
    # 用于部署基于FastAPI框架的异步PythonWeb应用程序
    uvicorn.run(app, host="0.0.0.0", port=PORT)
