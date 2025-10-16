import os
import requests
import logging
import json
from flask import Flask, request, jsonify
# 导入Celery相关模块（异步任务核心）
from celery import Celery
from celery.result import AsyncResult

# ---------------------- 基础配置初始化 ----------------------
app = Flask(__name__)
# 日志配置（保留原有逻辑）
app.logger.setLevel(logging.INFO)

# 1. AIFlowy配置（建议从环境变量读取，避免硬编码）
AIFLOWY_API_BASE = os.getenv("AIFLOWY_API_BASE", "http://10.0.0.19:8080")
AIFLOWY_WORKFLOW_ID = os.getenv("AIFLOWY_WORKFLOW_ID", "335639084029775872")

# 2. Celery异步任务配置（使用Redis作为任务队列和结果存储）
# Redis连接地址：默认本地Redis（无需密码），生产环境需配置密码和远程地址
# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_host = 'r-2vcvlqn3xxvgrh75hcpd.redis.cn-chengdu.rds.aliyuncs.com'
redis_port = 6379
redis_db = 3
redis_password = '5IevEcX3C7BhLNZR'

# 构建Redis URL
REDIS_URL = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"

# 初始化Celery
celery = Celery(
    app.name,  # 任务名称前缀
    broker=REDIS_URL,  # 任务队列：存放待处理的任务
    backend=REDIS_URL  # 结果存储：存放任务执行结果
)
celery.conf.update(app.config)  # 同步Flask配置


# ---------------------- 核心工具函数 ----------------------
def get_signed_oss_content(signed_url):
    """从带签名的OSS URL获取文件内容"""
    try:
        response = requests.get(
            signed_url,
            timeout=15,
            headers={"User-Agent": "Flask-OSS-Client/1.0"}
        )
        if response.status_code != 200:
            app.logger.error(f"OSS访问失败，状态码: {response.status_code}, 响应: {response.text}")
            return None
        # 处理中文乱码
        content = response.content.decode(response.apparent_encoding or 'utf-8')
        app.logger.info(f"成功获取OSS文件内容，长度: {len(content)}字符")
        return content
    except requests.exceptions.Timeout:
        app.logger.error("访问OSS超时")
        return None
    except requests.exceptions.SSLError:
        app.logger.error("OSS SSL证书验证失败")
        return None
    except Exception as e:
        app.logger.error(f"获取OSS内容异常: {str(e)}")
        return None

def get_local_file_content(file_path):
    """从本地文件路径获取文件内容"""
    try:
        if not os.path.exists(file_path):
            app.logger.error(f"本地文件不存在: {file_path}")
            return None
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            app.logger.info(f"成功读取本地文件内容，长度: {len(content)}字符")
            return content
    except Exception as e:
        app.logger.error(f"读取本地文件异常: {str(e)}")
        return None

def preprocess_input_data(raw_data):
    """预处理输入数据，确保usr_infor参数能正确处理"""
    try:
        app.logger.info(f"=== 开始数据预处理 ===")
        app.logger.info(f"原始数据类型: {type(raw_data)}")
        app.logger.info(f"原始数据长度: {len(str(raw_data))} 字符")
        app.logger.info(f"原始数据预览: {str(raw_data)[:300]}...")
        
        # 确保数据是字符串格式
        if not isinstance(raw_data, str):
            raw_data = str(raw_data)
        
        # 去除外层引号（如果存在双重转义）
        if raw_data.startswith('"') and raw_data.endswith('"'):
            app.logger.info("检测到外层引号，进行去除")
            raw_data = raw_data[1:-1]
        
        # 处理转义字符 - 将 \r\n 转换为实际的换行符
        # 注意：这里要处理的是字符串中的转义序列，不是实际的字符
        raw_data = raw_data.replace('\\r\\n', '\n').replace('\\r', '\n').replace('\\n', '\n')
        
        # 尝试解析为JSON并重新格式化
        try:
            parsed_data = json.loads(raw_data)
            app.logger.info("成功解析为JSON，重新格式化")
            # 重新格式化为紧凑的JSON字符串，去除不必要的空白字符
            formatted_data = json.dumps(parsed_data, ensure_ascii=False, separators=(',', ':'))
            app.logger.info(f"格式化后数据长度: {len(formatted_data)} 字符")
            app.logger.info(f"格式化后数据预览: {formatted_data[:300]}...")
            return formatted_data
        except json.JSONDecodeError as e:
            app.logger.info(f"不是有效的JSON格式: {str(e)}")
            # 如果不是JSON，进行基本的文本清理
            cleaned_data = raw_data.strip()
            # 移除多余的空白字符，但保留基本的换行结构
            cleaned_data = ' '.join(cleaned_data.split())
            app.logger.info(f"文本清理后数据长度: {len(cleaned_data)} 字符")
            
            # 对于清理后的数据，再次尝试解析为JSON（处理格式化后的情况）
            try:
                parsed_data = json.loads(cleaned_data)
                app.logger.info("清理后数据成功解析为JSON，重新格式化")
                formatted_data = json.dumps(parsed_data, ensure_ascii=False, separators=(',', ':'))
                app.logger.info(f"最终格式化数据长度: {len(formatted_data)} 字符")
                return formatted_data
            except json.JSONDecodeError:
                app.logger.info("清理后数据仍不是有效的JSON格式，返回清理后的文本")
                return cleaned_data
            
    except Exception as e:
        app.logger.error(f"数据预处理失败: {str(e)}")
        app.logger.info("返回原始数据")
        return str(raw_data)  # 出错时返回原始数据

def callback_frontend(unique_id):
    """回调前端接口，通知任务完成"""
    try:
        # 前端回调接口的URL（需要配置或从环境变量获取）
        callback_url = os.getenv("FRONTEND_CALLBACK_URL", "http://localhost:3000/advisor/ai/report/complete")
        
        response = requests.post(
            callback_url,
            json={"unique_id": unique_id},
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            app.logger.info(f"前端回调成功: unique_id={unique_id}")
            return True
        else:
            app.logger.warning(f"前端回调失败，状态码: {response.status_code}")
            return False
            
    except Exception as e:
        app.logger.error(f"前端回调异常: {str(e)}")
        return False

def call_aiflowy_workflow(prompt):
    """调用AIFlowy工作流"""
    try:
        # 构建请求URL
        url = f"{AIFLOWY_API_BASE}/api/v1/aiWorkflow/runningStream"
        print(url)
        
        # 预处理输入数据
        cleaned_prompt = preprocess_input_data(prompt)
        
        # 保持原有的payload格式不变
        payload = {
            "id": AIFLOWY_WORKFLOW_ID,
            "variables": {
                "usr_infor": cleaned_prompt  # 使用预处理后的数据
            }
        }
        
        app.logger.info(f"=== 开始调用AIFlowy工作流 ===")
        app.logger.info(f"请求URL: {url}")
        app.logger.info(f"工作流ID: {AIFLOWY_WORKFLOW_ID}")
        app.logger.info(f"预处理后数据长度: {len(cleaned_prompt)} 字符")
        app.logger.info(f"预处理后数据预览: {cleaned_prompt[:200]}...")
        
        # 发送POST请求
        #response = requests.post(
        #    url,
        #    json=payload,
        #    timeout=180,
        #    headers={"Content-Type": "application/json"}
        #)
        response = requests.post(
            url,
            json=payload,
            timeout=(30, 600),  # 连接超时30秒，读取超时600秒(10分钟)
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            },
            stream=True  # 启用流式响应
        )
        
        app.logger.info(f"AIFlowy响应状态码: {response.status_code}")
        app.logger.info(f"AIFlowy响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_text = response.text
            app.logger.info(f"AIFlowy响应长度: {len(response_text)} 字符")
            app.logger.info(f"AIFlowy响应内容: {response_text[:1500]}...")  # 显示前1500字符
            
            # 检查响应是否为空
            if not response_text or response_text.strip() == "":
                app.logger.error("AIFlowy返回空响应")
                return None
            
            # 检查响应是否包含SSE格式
            if 'data:' in response_text:
                app.logger.info("检测到SSE格式响应")
            else:
                app.logger.warning("未检测到SSE格式响应，可能是其他格式")
            
            return response_text
        else:
            app.logger.error(f"AIFlowy调用失败，状态码: {response.status_code}")
            app.logger.error(f"AIFlowy错误响应: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        app.logger.error("AIFlowy调用超时")
        return None
    except requests.exceptions.ConnectionError:
        app.logger.error("AIFlowy连接错误")
        return None
    except Exception as e:
        app.logger.error(f"AIFlowy调用异常: {str(e)}")
        app.logger.error(f"异常详情: {str(e)}", exc_info=True)
        return None

def handle_streaming_response(stream_response):
    """处理AIFlowy的流式响应"""
    try:
        # 添加调试日志：打印原始响应
        app.logger.info(f"=== 开始处理流式响应 ===")
        app.logger.info(f"原始响应长度: {len(stream_response)} 字符")
        app.logger.info(f"原始响应内容: {stream_response[:1000]}...")  # 增加到1000字符
        
        # 检查响应是否为空
        if not stream_response or stream_response.strip() == "":
            app.logger.error("流式响应为空")
            return None
        
        # 解析SSE格式的流式数据
        lines = stream_response.strip().split('\n')
        final_result = None
        parsed_lines = 0
        all_results = []  # 收集所有可能的结果
        
        app.logger.info(f"解析到 {len(lines)} 行SSE数据")
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            app.logger.info(f"=== 处理第 {i+1} 行 ===")
            app.logger.info(f"行内容: {line}")
            
            # 处理SSE格式的data:行
            if line.startswith('data:'):
                # 提取data后面的内容
                data_content = line[5:].strip()  # 去掉'data:'前缀
                app.logger.info(f"提取的data内容: {data_content}")
                
                # 跳过空行
                if not data_content:
                    app.logger.info("跳过空行")
                    continue
                
                try:
                    # 尝试解析JSON
                    data_json = json.loads(data_content)
                    parsed_lines += 1
                    app.logger.info(f"成功解析JSON: {json.dumps(data_json, ensure_ascii=False)}")
                    
                    # 检查JSON结构 - 更详细的调试
                    app.logger.info(f"JSON键列表: {list(data_json.keys())}")
                    
                    if 'content' in data_json:
                        content = data_json['content']
                        app.logger.info(f"content键内容: {list(content.keys())}")
                        
                        # 检查execResult - 最终结果
                        if 'execResult' in content:
                            app.logger.info("找到execResult字段")
                            exec_result = content['execResult']
                            app.logger.info(f"execResult键内容: {list(exec_result.keys())}")
                            
                            if 'output' in exec_result:
                                final_result = exec_result['output']
                                app.logger.info("=== 找到execResult中的最终结果 ===")
                                app.logger.info(f"最终结果长度: {len(final_result)} 字符")
                                app.logger.info(f"最终结果预览: {final_result[:300]}...")
                                all_results.append(('execResult', final_result))
                        
                        # 检查res - 中间结果
                        if 'res' in content:
                            app.logger.info("找到res字段")
                            res = content['res']
                            app.logger.info(f"res键内容: {list(res.keys())}")
                            
                            if 'output' in res:
                                intermediate_result = res['output']
                                app.logger.info("=== 找到中间节点的输出结果 ===")
                                app.logger.info(f"中间结果长度: {len(intermediate_result)} 字符")
                                app.logger.info(f"中间结果预览: {intermediate_result[:300]}...")
                                all_results.append(('res', intermediate_result))
                        
                        # 检查其他可能的输出字段
                        for key in ['result', 'answer', 'response', 'data']:
                            if key in content:
                                app.logger.info(f"找到其他输出字段: {key}")
                                other_result = content[key]
                                if isinstance(other_result, str) and len(other_result) > 10:
                                    app.logger.info(f"其他字段内容长度: {len(other_result)} 字符")
                                    all_results.append((key, other_result))
                    
                    # 检查其他可能的顶级字段
                    for key in ['result', 'output', 'answer', 'response']:
                        if key in data_json:
                            app.logger.info(f"找到顶级字段: {key}")
                            top_result = data_json[key]
                            if isinstance(top_result, str) and len(top_result) > 10:
                                app.logger.info(f"顶级字段内容长度: {len(top_result)} 字符")
                                all_results.append((f'top_{key}', top_result))
                        
                except json.JSONDecodeError as e:
                    app.logger.info(f"JSON解析失败: {str(e)}")
                    app.logger.info(f"无法解析的内容: {data_content}")
                    # 尝试检查是否是其他格式
                    if len(data_content) > 50 and ('{' in data_content or '}' in data_content):
                        app.logger.info("内容包含JSON标记但解析失败，可能是格式问题")
                    continue
        
        app.logger.info(f"=== SSE解析完成 ===")
        app.logger.info(f"总共解析了 {parsed_lines} 行JSON数据")
        app.logger.info(f"收集到的结果数量: {len(all_results)}")
        
        # 选择最佳结果
        if all_results:
            # 优先选择execResult的结果
            exec_results = [result for source, result in all_results if source == 'execResult']
            if exec_results:
                final_result = exec_results[0]
                app.logger.info("使用execResult中的结果作为最终结果")
            else:
                # 其次选择res的结果
                res_results = [result for source, result in all_results if source == 'res']
                if res_results:
                    final_result = res_results[0]
                    app.logger.info("使用res中的结果作为最终结果")
                else:
                    # 使用最后一个结果
                    final_result = all_results[-1][1]
                    app.logger.info(f"使用{all_results[-1][0]}中的结果作为最终结果")
            
            app.logger.info(f"选择的最终结果长度: {len(final_result)} 字符")
            app.logger.info(f"选择的最终结果预览: {final_result[:300]}...")
            
            # 尝试解析和格式化结果
            try:
                app.logger.info("开始解析最终结果中的JSON字符串")
                
                # 如果final_result是字符串形式的JSON，解析它
                if isinstance(final_result, str):
                    # 检查是否是JSON格式
                    if final_result.strip().startswith('{') and final_result.strip().endswith('}'):
                        try:
                            parsed_result = json.loads(final_result)
                            formatted_result = json.dumps(parsed_result, ensure_ascii=False, indent=2)
                            app.logger.info("成功解析并格式化JSON结果")
                            app.logger.info(f"格式化结果长度: {len(formatted_result)} 字符")
                            return formatted_result
                        except json.JSONDecodeError:
                            app.logger.info("最终结果不是有效的JSON字符串，直接返回")
                            return final_result
                    else:
                        app.logger.info("最终结果不是JSON格式，直接返回")
                        return final_result
                else:
                    # 如果是字典或其他类型，转换为JSON
                    formatted_result = json.dumps(final_result, ensure_ascii=False, indent=2)
                    app.logger.info("最终结果不是字符串，转换为JSON格式")
                    return formatted_result
                    
            except Exception as e:
                app.logger.error(f"结果格式化失败: {str(e)}")
                app.logger.info("直接返回原始结果")
                return final_result
        else:
            # 如果没有找到任何结果，记录详细警告并返回原始响应
            app.logger.warning("未在流式响应中找到任何结果")
            app.logger.warning(f"原始响应前2000字符: {stream_response[:2000]}")
            app.logger.warning("返回原始响应")
            return stream_response
            
    except Exception as e:
        app.logger.error(f"处理流式响应异常: {str(e)}")
        app.logger.error(f"异常详情: {str(e)}", exc_info=True)
        return None


# ---------------------- 异步任务（核心新增） ----------------------
@celery.task(bind=True, track_started=True)
def async_process_oss_data(self, signed_oss_url, unique_id):
    """
    异步处理OSS数据的任务（由Celery Worker执行，不阻塞Flask接口）
    :param self: 任务自身实例（用于更新任务状态）
    :param signed_oss_url: 带签名的OSS URL
    :param unique_id: 前端生成的唯一识别ID
    :return: 处理结果（成功/失败信息）
    """
    try:
        # 1. 更新任务状态为「处理中」，可在查询接口中显示进度
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "开始处理OSS数据",
                "oss_url": signed_oss_url,
                "unique_id": unique_id,
                "step": 1,
                "total_steps": 3
            }
        )

        # 2. 调用原有工具函数获取OSS内容（步骤1）
        oss_content = get_signed_oss_content(signed_oss_url)
        if not oss_content:
            # OSS内容获取失败，返回错误信息
            return {
                "success": False,
                "message": "无法获取OSS文件内容，请检查URL有效性或签名是否过期",
                "oss_url": signed_oss_url,
                "result": None
            }

        # 更新任务状态（步骤2完成）
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "OSS内容获取成功，开始调用AIFlowy工作流",
                "oss_url": signed_oss_url,
                "step": 2,
                "total_steps": 3
            }
        )

        # 3. 调用AIFlowy工作流（步骤3）
        app.logger.info(f"[任务{self.request.id}] 开始调用AIFlowy工作流")
        app.logger.info(f"**********oss_content内容是*************",oss_content)
        agent_response = call_aiflowy_workflow(oss_content)

        # 更新任务状态（步骤3完成）
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "工作流调用完成，正在整理结果",
                "oss_url": signed_oss_url,
                "unique_id": unique_id,
                "step": 3,
                "total_steps": 3
            }
        )

        # 4. 处理工作流响应
        if not agent_response:
            app.logger.error(f"[任务{self.request.id}] AIFlowy工作流调用失败")
            return {
                "success": False,
                "message": "AIFlowy工作流处理失败",
                "oss_url": signed_oss_url,
                "unique_id": unique_id,
                "result": None
            }

        # 5. 处理流式响应
        processed_result = handle_streaming_response(agent_response)
        if not processed_result:
            app.logger.error(f"[任务{self.request.id}] 流式响应处理失败")
            return {
                "success": False,
                "message": "流式响应处理失败",
                "oss_url": signed_oss_url,
                "unique_id": unique_id,
                "result": None
            }

        # 6. 处理成功，返回结果
        app.logger.info(f"[任务{self.request.id}] 处理完成，结果已保存")
        
        # 7. 回调前端接口
        if unique_id:
            callback_success = callback_frontend(unique_id)
            app.logger.info(f"[任务{self.request.id}] 前端回调结果: {'成功' if callback_success else '失败'}")
        
        return {
            "success": True,
            "message": "OSS数据处理成功",
            "oss_url": signed_oss_url,
            "unique_id": unique_id,
            "result": processed_result  # AIFlowy工作流分析结果
        }

    except Exception as e:
        # 捕获所有异常，确保任务状态正常更新
        app.logger.error(f"[任务{self.request.id}] 处理异常: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"处理过程异常: {str(e)}",
            "oss_url": signed_oss_url,
            "result": None
        }


# ---------------------- 接口（核心新增/修改） ----------------------
@app.route('/submit-task', methods=['POST'])
def submit_task():
    """
    1. 任务提交接口（替代原有同步接口）
    功能：接收OSS URL，提交异步任务，立即返回任务ID（不阻塞）
    请求体：{"signed_oss_url": "带签名的OSS URL"}
    响应：任务ID和初始状态
    """
    try:
        # 解析请求参数（与原接口逻辑一致）
        request_data = request.get_json()
        if not request_data or "signed_oss_url" not in request_data or "unique_id" not in request_data:
            return jsonify({
                "success": False,
                "message": "请求参数缺失，需包含signed_oss_url和unique_id"
            }), 400

        signed_oss_url = request_data["signed_oss_url"]
        unique_id = request_data["unique_id"]
        app.logger.info(f"收到任务提交请求，OSS URL: {signed_oss_url}")

        # 关键：提交任务到Celery队列（立即返回，不执行具体处理）
        # delay()方法会将任务放入队列，由Celery Worker后台执行
        task = async_process_oss_data.delay(signed_oss_url, unique_id)

        # 立即返回任务ID和状态（前端拿到ID后可调用查询接口）
        return jsonify({
            "success": True,
            "message": "任务已提交，正在后台处理",
            "task_id": task.id,  # 唯一任务ID（用于查询结果）
            "task_status": "PENDING",  # 初始状态：等待执行
            "oss_url": signed_oss_url
        }), 202  # 202状态码：请求已接受，正在处理

    except Exception as e:
        app.logger.error(f"任务提交异常: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"任务提交失败: {str(e)}"
        }), 500


@app.route('/query-task/<task_id>', methods=['GET'])
def query_task(task_id):
    """
    2. 任务查询接口
    功能：通过任务ID查询处理状态和结果（前端可定期调用）
    路径参数：task_id（任务提交时返回的ID）
    响应：任务状态（等待/处理中/成功/失败）+ 结果（若成功）
    """
    try:
        # 通过任务ID获取任务实例
        task = AsyncResult(task_id, app=celery)

        # 根据任务状态返回不同信息
        if task.state == "PENDING":
            # 任务未开始（等待Worker执行）
            response = {
                "success": True,
                "task_id": task_id,
                "task_state": task.state,
                "status": "任务等待中，请稍后查询",
                "result": None
            }
        elif task.state == "PROGRESS":
            # 任务处理中（返回进度信息）
            try:
                # 安全地访问任务信息
                task_info = task.info if isinstance(task.info, dict) else {}
                response = {
                    "success": True,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": task_info.get("status", "处理中"),
                    "progress": f"{task_info.get('step', 1)}/{task_info.get('total_steps', 3)}",
                    "oss_url": task_info.get("oss_url", ""),
                    "unique_id": task_info.get("unique_id"),  # 添加 unique_id
                    "result": None
                }
            except Exception as e:
                response = {
                    "success": True,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": "任务处理中",
                    "progress": "1/3",
                    "oss_url": "",
                    "unique_id": None,
                    "result": None
                }
        elif task.state == "SUCCESS":
            # 任务成功（返回处理结果）
            try:
                task_result = task.result if isinstance(task.result, dict) else {}
                response = {
                    "success": True,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": "任务处理成功",
                    "unique_id": task_result.get("unique_id"),  # 添加 unique_id
                    "data": task_result  # task.result 是 async_process_oss_data 的返回值
                }
            except Exception as e:
                response = {
                    "success": True,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": "任务处理成功",
                    "unique_id": None,
                    "data": {"message": "任务完成但结果格式异常"}
                }
        else:
            # 任务失败（状态可能是FAILURE等）
            try:
                task_result = task.result if isinstance(task.result, dict) else {}
                response = {
                    "success": False,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": "任务处理失败",
                    "unique_id": task_result.get("unique_id"),  # 添加 unique_id
                    "error_message": task_result.get("message", str(task.info)) if task_result else str(task.info),
                    "result": None
                }
            except Exception as e:
                response = {
                    "success": False,
                    "task_id": task_id,
                    "task_state": task.state,
                    "status": "任务处理失败",
                    "unique_id": None,
                    "error_message": f"任务失败: {str(e)}",
                    "result": None
                }

        return jsonify(response)

    except Exception as e:
        app.logger.error(f"查询任务异常: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"查询任务失败: {str(e)}",
            "task_id": task_id
        }), 500


@app.route('/task-notify', methods=['POST'])
def task_notify():
    """
    3. 任务完成通知接口（预留，供后续扩展）
    功能：异步任务处理完成后，主动调用此接口通知前端（需前端提供回调URL）
    目前可先保留，后续可结合WebSocket或前端回调URL使用
    """
    notify_data = request.get_json()
    app.logger.info(f"收到任务完成通知: {notify_data}")
    # 后续可扩展：验证通知合法性、推送结果到前端等
    return jsonify({
        "success": True,
        "message": "通知已接收"
    })


# ---------------------- 服务启动（新增Celery提示） ----------------------
if __name__ == '__main__':
    # 启动提示（初学者关键步骤）
    # print("=" * 50)
    # print("服务启动前请先完成以下步骤：")
    # print("1. 启动Redis服务（本地默认地址：redis://localhost:6379/0）")
    # print("2. 启动Celery Worker（执行异步任务）：")
    # print("   命令：celery -A app.celery worker --loglevel=info")
    # print("3. 启动本Flask服务（接收请求和查询）")
    # print("=" * 50)
    print("=" * 50)
    print("服务启动前请先完成以下步骤：")
    print("1. 确保阿里云Redis服务可访问")
    print(f"2. Redis地址: {redis_host}:{redis_port}, DB: {redis_db}")
    print("3. 启动Celery Worker（执行异步任务）：")
    print("   命令：celery -A app.celery worker --loglevel=info")
    print("4. 启动本Flask服务（接收请求和查询）")
    print("=" * 50)

    # Flask服务启动（保留原有配置）
    app.run(
        host=os.getenv("FLASK_HOST", "0.0.0.0"),
        port=int(os.getenv("FLASK_PORT", 5002)),
        debug=os.getenv("FLASK_DEBUG", "False").lower() == "true"
    )
# import os
# import requests
# import logging  # 使用标准库的logging模块
# from http import HTTPStatus
# from flask import Flask, request, jsonify
# from dashscope import Application
#
# app = Flask(__name__)
# # 配置日志
# app.logger.setLevel(logging.INFO)  # 现在使用的是标准logging模块的INFO
#
# # 阿里云百炼智能体配置（请替换为你的实际信息）
# DASHSCOPE_API_KEY = "sk-8ac6ce8ab2f24126b166604f97f0af81"  # 建议从环境变量获取：os.getenv("DASHSCOPE_API_KEY")
# BAILIAN_APP_ID = "55a12bae78c94eedb494b301787bc833"
#
#
# def get_signed_oss_content(signed_url):
#     """
#     从带签名的OSS URL获取文件内容
#     :param signed_url: 带签名的OSS文件访问URL
#     :return: 文件内容字符串，获取失败返回None
#     """
#     try:
#         # 设置合理的超时时间
#         response = requests.get(
#             signed_url,
#             timeout=15,
#             headers={"User-Agent": "Flask-OSS-Client/1.0"}
#         )
#
#         # 检查HTTP响应状态码
#         if response.status_code != HTTPStatus.OK:
#             app.logger.error(f"OSS访问失败，状态码: {response.status_code}, 响应: {response.text}")
#             return None
#
#         # 尝试解析内容编码（处理中文乱码）
#         content = response.content.decode(response.apparent_encoding or 'utf-8')
#         app.logger.info(f"成功获取OSS文件内容，长度: {len(content)}字符")
#         return content
#
#     except requests.exceptions.Timeout:
#         app.logger.error("访问OSS超时")
#         return None
#     except requests.exceptions.SSLError:
#         app.logger.error("OSS SSL证书验证失败")
#         return None
#     except Exception as e:
#         app.logger.error(f"获取OSS内容异常: {str(e)}")
#         return None
#
#
# @app.route('/process-oss-data', methods=['POST'])
# def process_oss_data():
#     """
#     处理带签名OSS URL的接口
#     请求体格式: {"signed_oss_url": "带签名的OSS文件URL"}
#     """
#     try:
#         # 1. 解析请求参数
#         request_data = request.get_json()
#         if not request_data or "signed_oss_url" not in request_data:
#             return jsonify({
#                 "success": False,
#                 "message": "请求参数缺失，需包含signed_oss_url"
#             }), 400
#
#         signed_oss_url = request_data["signed_oss_url"]
#         app.logger.info(f"收到处理请求，OSS URL: {signed_oss_url}")
#
#         # 2. 从签名URL获取文件内容
#         oss_content = get_signed_oss_content(signed_oss_url)
#         if not oss_content:
#             return jsonify({
#                 "success": False,
#                 "message": "无法获取OSS文件内容，请检查URL有效性或签名是否过期"
#             }), 500
#
#         # 3. 调用阿里云百炼智能体
#         app.logger.info("开始调用阿里云百炼智能体")
#         response = Application.call(
#             api_key=DASHSCOPE_API_KEY,
#             app_id=BAILIAN_APP_ID,
#             prompt="请分析处理以下数据并给出结果：\n{content}".format(content=oss_content),
#             # 如需传递结构化参数可使用biz_params
#             # biz_params={"data": oss_content}
#         )
#
#         # 4. 处理智能体响应
#         if response.status_code != HTTPStatus.OK:
#             app.logger.error(f"智能体调用失败: {response.message} (Request ID: {response.request_id})")
#             return jsonify({
#                 "success": False,
#                 "request_id": response.request_id,
#                 "error_code": response.status_code,
#                 "message": f"智能体处理失败: {response.message}"
#             }), 500
#
#         app.logger.info(f"智能体处理成功 (Request ID: {response.request_id})")
#         return jsonify({
#             "success": True,
#             "request_id": response.request_id,
#             "oss_url": signed_oss_url,
#             "result": response.output.text
#         })
#
#     except Exception as e:
#         app.logger.error(f"接口处理异常: {str(e)}", exc_info=True)
#         return jsonify({
#             "success": False,
#             "message": f"接口内部错误: {str(e)}"
#         }), 500
#
#
# if __name__ == '__main__':
#     # 生产环境请使用Gunicorn等WSGI服务器，并关闭debug模式
#     app.run(
#         host=os.getenv("FLASK_HOST", "0.0.0.0"),
#         port=int(os.getenv("FLASK_PORT", 5000)),
#         debug=os.getenv("FLASK_DEBUG", "False").lower() == "true"
#     )
