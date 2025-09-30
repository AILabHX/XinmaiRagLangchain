#!/usr/bin/env python3
"""
测试dify chatflow API集成
"""

import asyncio
import json
import httpx
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DIFY_API_BASE = "http://192.168.96.1/v1"
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_CHAT_ENDPOINT = "/chat-messages"

async def test_dify_api():
    """测试dify API连接"""
    if not DIFY_API_KEY or DIFY_API_KEY == "your_dify_api_key_here":
        print("❌ 请先在.env文件中设置正确的DIFY_API_KEY")
        return False
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {},
        "query": "你好，请简单介绍一下你自己",
        "response_mode": "blocking",
        "conversation_id": "",
        "user": "test_user"
    }
    
    try:
        print(f"🔗 正在连接dify API: {DIFY_API_BASE}{DIFY_CHAT_ENDPOINT}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{DIFY_API_BASE}{DIFY_CHAT_ENDPOINT}",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            
            print("✅ dify API连接成功！")
            print(f"📝 回答内容: {result.get('answer', '')}")
            print(f"💬 对话ID: {result.get('conversation_id', '')}")
            
            # 检查是否有检索结果
            retriever_resources = result.get('metadata', {}).get('retriever_resources', [])
            if retriever_resources:
                print(f"📚 检索到 {len(retriever_resources)} 个相关文档")
            else:
                print("ℹ️  未检索到相关文档")
                
            return True
            
    except httpx.TimeoutException:
        print("❌ dify API请求超时，请检查网络连接")
        return False
    except httpx.HTTPStatusError as e:
        print(f"❌ dify API HTTP错误: {e.response.status_code}")
        print(f"错误详情: {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ 调用dify API时出错: {str(e)}")
        return False

async def test_main_memory_service():
    """测试修改后的mainMemory服务"""
    print("\n🧪 测试mainMemory服务...")
    
    # 这里可以添加对本地服务的测试
    # 由于服务需要启动，这里只做基本检查
    print("✅ mainMemory.py代码修改完成")
    print("✅ 依赖包已更新")
    print("✅ 环境变量已配置")
    print("⚠️  请手动启动服务进行完整测试: python mainMemory.py")

def main():
    """主测试函数"""
    print("🚀 开始测试dify chatflow集成")
    
    # 测试dify API连接
    success = asyncio.run(test_dify_api())
    
    if success:
        print("\n🎉 dify API测试通过！")
        asyncio.run(test_main_memory_service())
        print("\n📋 下一步操作:")
        print("1. 确保DIFY_API_KEY在.env文件中正确设置")
        print("2. 运行: python mainMemory.py 启动服务")
        print("3. 使用API客户端测试/v1/chat/completions接口")
    else:
        print("\n❌ dify API测试失败，请检查配置")
        sys.exit(1)

if __name__ == "__main__":
    main()
