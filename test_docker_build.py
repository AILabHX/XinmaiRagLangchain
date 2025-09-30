#!/usr/bin/env python3
"""
测试Docker构建配置
"""

import subprocess
import sys

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def test_docker_build():
    """测试Docker构建"""
    print("=== 测试Docker构建 ===")
    
    # 检查Docker是否安装
    returncode, stdout, stderr = run_command("docker --version")
    if returncode != 0:
        print("❌ Docker未安装")
        return False
    print(f"✅ Docker版本: {stdout.strip()}")
    
    # 检查Docker Compose是否安装
    returncode, stdout, stderr = run_command("docker-compose --version")
    if returncode != 0:
        print("❌ Docker Compose未安装")
        return False
    print(f"✅ Docker Compose版本: {stdout.strip()}")
    
    # 检查Dockerfile是否存在
    try:
        with open('Dockerfile', 'r', encoding='utf-8') as f:
            content = f.read()
        print("✅ Dockerfile存在")
    except FileNotFoundError:
        print("❌ Dockerfile不存在")
        return False
    
    # 检查docker-compose.yml是否存在
    try:
        with open('docker-compose.yml', 'r', encoding='utf-8') as f:
            content = f.read()
        print("✅ docker-compose.yml存在")
    except FileNotFoundError:
        print("❌ docker-compose.yml不存在")
        return False
    
    # 检查.env文件是否存在
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            content = f.read()
        print("✅ .env文件存在")
    except FileNotFoundError:
        print("⚠️  .env文件不存在（需要创建）")
    
    # 检查必需的文件
    required_files = [
        'mainMemory.py',
        'apiMain.py', 
        'requirements_XM.txt',
        'prompt_template_memory.txt'
    ]
    
    missing_files = []
    for file in required_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                pass
        except FileNotFoundError:
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少必需文件: {', '.join(missing_files)}")
        return False
    else:
        print("✅ 所有必需文件都存在")
    
    # 检查目录结构
    required_dirs = ['chromaDB', 'input']
    missing_dirs = []
    for dir_name in required_dirs:
        import os
        if not os.path.exists(dir_name) or not os.path.isdir(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print(f"⚠️  缺少目录: {', '.join(missing_dirs)}（部署时需要创建）")
    else:
        print("✅ 所有必需目录都存在")
    
    print("\n=== 测试完成 ===")
    return True

if __name__ == "__main__":
    success = test_docker_build()
    if success:
        print("✅ Docker配置测试通过")
        print("\n下一步：")
        print("1. 编辑 .env 文件配置您的API密钥")
        print("2. 上传所有文件到阿里云服务器")
        print("3. 运行 deploy.sh 进行部署")
    else:
        print("❌ Docker配置测试失败")
        sys.exit(1)
