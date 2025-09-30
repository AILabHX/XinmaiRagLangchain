@echo off
echo ========================================
echo    XinMai-RagLangChain Windows部署脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

REM 检查Git是否安装
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到Git，请先安装Git
    pause
    exit /b 1
)

echo ✅ 环境检查通过
echo.

REM 设置项目路径
set PROJECT_PATH=%CD%
echo 项目路径：%PROJECT_PATH%

REM 创建虚拟环境
echo 正在创建Python虚拟环境...
python -m venv api_env
if errorlevel 1 (
    echo ❌ 错误：创建虚拟环境失败
    pause
    exit /b 1
)

echo ✅ 虚拟环境创建成功

REM 激活虚拟环境并安装依赖
echo 正在激活虚拟环境并安装依赖...
call api_env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 错误：依赖安装失败
    pause
    exit /b 1
)

echo ✅ 依赖安装成功

REM 配置生产环境
echo 正在配置生产环境...
if exist .env.production.template (
    if not exist .env (
        copy .env.production.template .env
        echo ✅ 生产环境配置文件已创建
        echo.
        echo ⚠️  重要：请编辑 .env 文件，配置以下信息：
        echo     - OPENAI_API_KEY
        echo     - 确认Redis配置正确
        echo     - 确认PROJECT_ROOT路径正确
        echo.
    ) else (
        echo ℹ️  .env 文件已存在，跳过创建
    )
) else (
    echo ❌ 错误：未找到 .env.production.template 文件
    pause
    exit /b 1
)

REM 测试Redis连接
echo 正在测试Redis连接...
python test_redis_connection.py
if errorlevel 1 (
    echo ❌ 错误：Redis连接测试失败
    echo 请检查 .env 文件中的Redis配置
    pause
    exit /b 1
)

echo ✅ Redis连接测试成功

REM 测试阿里云Redis连接
echo 正在测试阿里云Redis连接...
python test_aliyun_redis.py
if errorlevel 1 (
    echo ⚠️  警告：阿里云Redis连接测试失败
    echo 请确保阿里云Redis配置正确且网络可达
) else (
    echo ✅ 阿里云Redis连接测试成功
)

echo.
echo ========================================
echo 🎉 部署完成！
echo ========================================
echo.
echo 下一步操作：
echo 1. 编辑 .env 文件，配置必要的环境变量
echo 2. 运行以下命令启动API服务：
echo    call api_env\Scripts\activate
echo    python apiMain.py
echo 3. 访问 http://localhost:5000/docs 验证部署
echo.
echo 详细部署说明请参考 WINDOWS_SERVER_DEPLOYMENT_GUIDE.md
echo.

pause
