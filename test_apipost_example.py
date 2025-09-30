#!/usr/bin/env python3
"""
APIPOST测试示例脚本
用于验证/v1/chat/completions接口
"""

import json
import httpx
import asyncio

async def test_chat_completions():
    """测试聊天完成接口"""
    
    # 测试URL
    url = "http://localhost:8013/v1/chat/completions"
    
    # 请求体（与APIPOST中使用的相同）
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "你好，请介绍一下高血压的预防方法"
            }
        ],
        "stream": true,
        "user": "test_user_001",
        "conversation_id": "test_conversation_001"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        print("🚀 开始测试/v1/chat/completions接口")
        print(f"📝 请求URL: {url}")
        print(f"📦 请求体: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            
            print(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ 接口测试成功！")
                print(f"📄 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                print(f"❌ 接口测试失败: {response.text}")
                
    except httpx.ConnectError:
        print("❌ 无法连接到服务，请确保mainMemory.py正在运行")
    except Exception as e:
        print(f"❌ 测试过程中出错: {str(e)}")

async def test_health_check():
    """测试健康检查接口"""
    try:
        url = "http://localhost:8013/health"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            print(f"\n🏥 健康检查: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 健康检查失败: {str(e)}")

async def main():
    """主测试函数"""
    print("=" * 50)
    print("APIPOST接口测试示例")
    print("=" * 50)
    
    # 先测试健康检查
    await test_health_check()
    
    # 再测试聊天接口
    await test_chat_completions()
    
    print("\n📋 APIPOST配置说明:")
    print("1. 方法: POST")
    print("2. URL: http://localhost:8013/v1/chat/completions")
    print("3. Headers: Content-Type: application/json")
    print("4. Body: 使用上面示例的JSON格式")
    print("5. 确保mainMemory.py服务正在运行")

if __name__ == "__main__":
    asyncio.run(main())
