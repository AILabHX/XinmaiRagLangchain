#!/usr/bin/env python3
"""
调试dify API连接的脚本
用于诊断"Expecting value: line 1 column 1 (char 0)"错误
"""

import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# dify相关配置
DIFY_API_BASE = "http://192.168.96.1/v1"
DIFY_API_KEY = os.getenv("DIFY_API_KEY")
DIFY_CHAT_ENDPOINT = "/chat-messages"

async def test_dify_connection():
    """测试dify API连接"""
    
    print("🔧 开始调试dify API连接...")
    print(f"📡 API地址: {DIFY_API_BASE}{DIFY_CHAT_ENDPOINT}")
    print(f"🔑 API密钥: {'已设置' if DIFY_API_KEY else '未设置'}")
    
    if not DIFY_API_KEY:
        print("❌ 错误：DIFY_API_KEY未配置")
        return False
    
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 测试不同的payload配置
    test_cases = [
        {
            "name": "基础测试 - 阻塞模式",
            "payload": {
                "inputs": {},
                "query": "你好",
                "response_mode": "blocking",
                "conversation_id": "",
                "user": "debug_user"
            }
        },
        {
            "name": "基础测试 - 流式模式",
            "payload": {
                "inputs": {},
                "query": "你好",
                "response_mode": "streaming",
                "conversation_id": "",
                "user": "debug_user"
            }
        },
        {
            "name": "带UUID的测试",
            "payload": {
                "inputs": {},
                "query": "你好",
                "response_mode": "blocking",
                "conversation_id": "12345678-1234-5678-1234-567812345678",
                "user": "debug_user"
            }
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 测试用例 {i}: {test_case['name']}")
            print(f"📦 请求体: {json.dumps(test_case['payload'], ensure_ascii=False, indent=2)}")
            
            try:
                # 发送请求
                response = await client.post(
                    f"{DIFY_API_BASE}{DIFY_CHAT_ENDPOINT}",
                    headers=headers,
                    json=test_case['payload']
                )
                
                print(f"📊 响应状态码: {response.status_code}")
                print(f"📋 响应头: {dict(response.headers)}")
                print(f"📄 原始响应内容: {repr(response.text)}")
                
                if response.status_code == 200:
                    if response.text.strip():
                        try:
                            result = response.json()
                            print(f"✅ JSON解析成功: {json.dumps(result, ensure_ascii=False, indent=2)}")
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON解析失败: {e}")
                    else:
                        print("⚠️ 响应为空")
                else:
                    print(f"❌ HTTP错误: {response.text}")
                    
            except httpx.TimeoutException:
                print("❌ 请求超时")
            except httpx.ConnectError:
                print("❌ 连接失败，请检查dify服务是否运行")
            except Exception as e:
                print(f"❌ 其他错误: {str(e)}")
    
    return True

async def test_health_endpoint():
    """测试dify健康检查接口"""
    print(f"\n🏥 测试dify健康检查接口...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{DIFY_API_BASE}/health")
            print(f"📊 健康检查状态码: {response.status_code}")
            print(f"📄 健康检查响应: {response.text}")
    except Exception as e:
        print(f"❌ 健康检查失败: {str(e)}")

async def main():
    """主函数"""
    print("=" * 60)
    print("🔧 dify API调试工具")
    print("=" * 60)
    
    # 测试健康检查
    await test_health_endpoint()
    
    # 测试API连接
    await test_dify_connection()
    
    print("\n📝 调试完成！")
    print("💡 如果看到'Expecting value: line 1 column 1 (char 0)'错误，")
    print("    通常意味着dify API返回了空响应或非JSON响应。")
    print("💡 请检查：")
    print("    1. dify服务是否正常运行")
    print("    2. API密钥是否正确")
    print("    3. 网络连接是否正常")

if __name__ == "__main__":
    asyncio.run(main())
