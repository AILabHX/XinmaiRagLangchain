#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook回调功能测试脚本
用于测试apiMain.py中的Webhook回调功能
"""

import requests
import json
import time
import threading
from flask import Flask, request, jsonify

# 模拟客户端Webhook接收服务器
app = Flask(__name__)
received_callbacks = []

@app.route('/ai/message/receive', methods=['POST'])
def receive_callback():
    """模拟客户端接收Webhook回调的接口"""
    data = request.get_json()
    print(f"📨 收到Webhook回调: {json.dumps(data, indent=2, ensure_ascii=False)}")
    received_callbacks.append({
        'timestamp': time.time(),
        'data': data
    })
    return jsonify({"success": True, "message": "回调接收成功"})

def run_webhook_server():
    """启动Webhook接收服务器"""
    print("🚀 启动Webhook接收服务器...")
    app.run(host='0.0.0.0', port=9090, debug=False, use_reloader=False)

def test_webhook_functionality():
    """测试Webhook回调功能"""
    
    # 启动Webhook接收服务器（在后台线程中）
    server_thread = threading.Thread(target=run_webhook_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # 等待服务器启动
    
    print("🧪 开始测试Webhook回调功能...")
    
    # 测试数据
    test_data = {
        "sessionId": "test-session-123",
        "messageId": "test-message-456",
        "content": "测试消息内容",
        "messageType": 0,
        "sendTime": "2024-01-01T12:00:00",
        "callbackUrl": "http://localhost:9090/ai/message/receive"
    }
    
    # 发送测试请求到API
    try:
        response = requests.post(
            "http://localhost:5000/api/ai/sessions/test-session-123/messages",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📤 API响应: {response.status_code}")
        if response.status_code == 202:
            print("✅ API接受请求成功")
            task_info = response.json()
            print(f"📋 任务信息: {json.dumps(task_info, indent=2, ensure_ascii=False)}")
            
            # 等待Webhook回调
            print("⏳ 等待Webhook回调...")
            timeout = 30  # 30秒超时
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if received_callbacks:
                    callback = received_callbacks[-1]
                    print("✅ Webhook回调接收成功!")
                    print(f"📊 回调数据: {json.dumps(callback['data'], indent=2, ensure_ascii=False)}")
                    return True
                time.sleep(1)
            
            print("❌ Webhook回调超时，未收到回调")
            return False
            
        else:
            print(f"❌ API请求失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {str(e)}")
        return False

if __name__ == '__main__':
    print("🔧 Webhook回调功能测试")
    print("=" * 50)
    
    # 检查API服务器是否运行
    try:
        health_check = requests.get("http://localhost:5000/docs", timeout=5)
        print("✅ API服务器运行正常")
    except:
        print("⚠️  API服务器未运行，请先启动apiMain.py")
        print("💡 启动命令: python apiMain.py")
        exit(1)
    
    # 运行测试
    success = test_webhook_functionality()
    
    if success:
        print("\n🎉 Webhook回调功能测试通过!")
    else:
        print("\n💥 Webhook回调功能测试失败!")
    
    print("=" * 50)
