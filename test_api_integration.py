import requests
import json

def test_submit_task():
    """测试 /submit-task 接口"""
    url = "http://127.0.0.1:5002/submit-task"
    
    # 测试数据
    data = {
        "signed_oss_url": "https://new-pulse-test.oss-cn-chengdu.aliyuncs.com/oss/250925模拟数据.txt?Expires=1757067312&OSSAccessKeyId=LTAI5tLU9RBJF3yVfZzgqND3&Signature=2ps7yXdL7dQ43B1xIgki8gK%2Bxp0%3D",
        "unique_id": "test_unique_id_001"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        print("=== 测试 /submit-task 接口 ===")
        print(f"请求URL: {url}")
        print(f"请求数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"\n=== 响应结果 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 202:
            result = response.json()
            print(f"\n✅ 接口调用成功!")
            print(f"任务ID: {result.get('task_id')}")
            print(f"unique_id: {data['unique_id']}")
            print(f"任务状态: {result.get('task_status')}")
            
            # 返回任务ID用于后续查询测试
            return result.get('task_id')
        else:
            print(f"❌ 接口调用失败")
            return None
            
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {str(e)}")
        return None

def test_query_task(task_id):
    """测试 /query-task 接口"""
    if not task_id:
        print("没有有效的任务ID，跳过查询测试")
        return
    
    url = f"http://127.0.0.1:5002/query-task/{task_id}"
    
    try:
        print(f"\n=== 测试 /query-task 接口 ===")
        print(f"查询URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        print(f"\n=== 查询结果 ===")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 查询成功!")
            print(f"任务状态: {result.get('task_state')}")
            print(f"unique_id: {result.get('unique_id')}")
        else:
            print(f"❌ 查询失败")
            
    except Exception as e:
        print(f"❌ 查询过程中出现异常: {str(e)}")

if __name__ == "__main__":
    print("开始测试 unique_id 功能集成...")
    print("=" * 50)
    
    # 测试提交任务
    task_id = test_submit_task()
    
    # 测试查询任务（如果有任务ID）
    if task_id:
        test_query_task(task_id)
    
    print("\n" + "=" * 50)
    print("测试完成!")
