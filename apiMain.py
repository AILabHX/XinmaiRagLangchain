
# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from pydantic import BaseModel, Field
from pydantic.functional_validators import field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
import requests
import json
import logging

app = Flask(__name__)

sessions = {} 
messages = {}


# 数据模型定义（对应Java的DTO/VO）
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

    @field_validator('messageType')
    def message_type_must_be_valid(cls, v):
        if v not in [0, 1, 2, 3, 4]:  # 与Java定义一致
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


# 统一响应格式生成函数
def api_response(success: bool, message: str, data: Any = None) -> Dict[str, Any]:
    return {
        "success": success,
        "message": message,
        "data": data
    }


# 1. 创建/发起新的会话接口
@app.route('/api/ai/sessions', methods=['POST'])
def create_session():
    try:
        # 解析并验证请求数据
        dto = CreateAiSessionDTO(**request.json)
        
        # 检查会话ID是否已存在
        if dto.sessionId in sessions:
            return jsonify(api_response(False, "会话已存在")), 400
        
        # 存储会话信息
        session_info = {
            "sessionId": dto.sessionId,
            "title": dto.title,
            "description": dto.description,
            "consultType": dto.consultType,
            "healthInfoUrl": dto.healthInfoUrl,
            "createTime": datetime.now().isoformat()
        }
        sessions[dto.sessionId] = session_info
        messages[dto.sessionId] = []  # 初始化消息列表
        
        return jsonify(api_response(
            True, 
            "会话创建成功",
            {
                "sessionId": dto.sessionId,
                "createTime": session_info["createTime"]
            }
        )), 201
    
    except Exception as e:
        return jsonify(api_response(False, str(e))), 400


# 2. 发送消息接口
@app.route('/api/ai/sessions/<sessionId>/messages', methods=['POST'])
def send_message(sessionId):
    try:
        # 解析并验证请求数据
        dto = SendMessageDTO(** request.json)
        
        # 验证路径ID与请求体ID一致
        if dto.sessionId != sessionId:
            logging.warning(f"路径会话ID与请求体不一致: 路径ID={sessionId}, 请求体ID={dto.sessionId}")
            return jsonify(api_response(False, "路径会话ID与请求体不一致")), 400
        
        # 检查会话是否存在
        if dto.sessionId not in sessions:
            return jsonify(api_response(False, "会话不存在")), 404
        
        # 处理发送时间（前端未传则用当前时间）
        sendTime = dto.sendTime or datetime.now().isoformat()
        
        # 存储用户消息
        user_message = {
            "messageId": dto.messageId,
            "sessionId": dto.sessionId,
            "messageType": dto.messageType,
            "content": dto.content,
            "sendTime": sendTime,
            "sender": "user"  # 标记发送者
        }
        messages[dto.sessionId].append(user_message)
        
        # 调用真实的LLM API进行回复
        ai_message_id = str(uuid.uuid4())[:8]  # 生成简短ID
        
        # 准备LLM API请求数据（严格按照apiMemoryTest.py格式）
        llm_url = "http://47.109.103.76:8013/v1/chat/completions"
        llm_headers = {"Content-Type": "application/json"}
        llm_data = {
            "messages": [{"role": "user", "content": dto.content}],
            "stream": False,
            "userId": dto.sessionId,
            "conversationId": dto.sessionId
        }
        
        try:
            # 发送请求到LLM API
            response = requests.post(llm_url, headers=llm_headers, data=json.dumps(llm_data))
            response.raise_for_status()  # 检查HTTP错误
            
            # 解析LLM响应
            llm_response = response.json()
            ai_content = llm_response['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            # LLM API调用失败时使用备用回复
            ai_content = f"抱歉，AI服务暂时不可用。错误信息: {str(e)}"
        except (KeyError, json.JSONDecodeError) as e:
            # 响应解析错误时使用备用回复
            ai_content = f"抱歉，AI响应解析错误。错误信息: {str(e)}"
        
        # 创建AI消息
        ai_message = {
            "messageId": ai_message_id,
            "sessionId": dto.sessionId,
            "messageType": 0,  # 文本回复
            "content": ai_content,
            "sendTime": datetime.now().isoformat(),
            "sender": "ai"  # 标记发送者
        }
        messages[dto.sessionId].append(ai_message)
        
        return jsonify(api_response(
            True,
            "消息处理成功",
            {
                "userMessageId": dto.messageId,
                "aiMessage": ai_message
            }
        )), 200
    
    except Exception as e:
        return jsonify(api_response(False, str(e))), 400


# 3. 分页查询消息接口
@app.route('/api/ai/sessions/<sessionId>/messages', methods=['GET'])
def query_messages(sessionId):
    try:
        # 解析查询参数并验证
        query_params = {
            "sessionId": sessionId,
            "startMessageId": request.args.get("startMessageId"),
            "pageNum": int(request.args.get("pageNum", 1)),
            "pageSize": int(request.args.get("pageSize", 10))
        }
        dto = QueryMessagePageDTO(**query_params)
        
        # 检查会话是否存在
        if dto.sessionId not in messages:
            return jsonify(api_response(False, "会话不存在")), 404
        
        # 获取会话消息列表（按时间倒序，最新的在前）
        session_messages = sorted(
            messages[dto.sessionId],
            key=lambda x: x["sendTime"],
            reverse=True
        )
        
        # 处理起始消息ID过滤
        if dto.startMessageId:
            start_index = next(
                (i for i, msg in enumerate(session_messages) 
                 if msg["messageId"] == dto.startMessageId),
                None
            )
            if start_index is not None:
                session_messages = session_messages[start_index+1:]  # 从起始消息之后开始取
        
        # 分页处理
        total = len(session_messages)
        start = (dto.pageNum - 1) * dto.pageSize
        end = start + dto.pageSize
        page_messages = session_messages[start:end]
        
        # 构建分页响应（移除sender字段，符合前端VO定义）
        response_data = {
            "total": total,
            "pageSize": dto.pageSize,
            "current": dto.pageNum,
            "records": [
                {k: v for k, v in msg.items() if k != "sender"} 
                for msg in page_messages
            ]
        }
        
        return jsonify(api_response(True, "查询成功", response_data)), 200
    
    except Exception as e:
        return jsonify(api_response(False, str(e))), 400


# 4. 结束会话接口（补充接口，用于完善流程）
@app.route('/api/ai/sessions/<sessionId>/end', methods=['POST'])
def end_session(sessionId):
    if sessionId not in sessions:
        return jsonify(api_response(False, "会话不存在")), 404
    
    # 标记会话状态为已结束
    sessions[sessionId]["status"] = "ended"
    sessions[sessionId]["endTime"] = datetime.now().isoformat()
    
    return jsonify(api_response(
        True, 
        "会话已结束",
        {"sessionId": sessionId, "endTime": sessions[sessionId]["endTime"]}
    )), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
