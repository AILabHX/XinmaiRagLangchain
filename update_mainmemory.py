#!/usr/bin/env python3
"""
更新 mainMemory.py 以支持环境变量配置
"""

import os

# 读取 mainMemory.py 内容
with open('mainMemory.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换硬编码的配置为环境变量读取
updated_content = content.replace(
    '# 设置langsmith环境变量\nos.environ["LANGCHAIN_TRACING_V2"] = "true"\nos.environ["LANGCHAIN_API_KEY"] = "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"',
    '# 设置langsmith环境变量\nos.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")\nos.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")'
)

updated_content = updated_content.replace(
    'CHROMADB_DIRECTORY = "chromaDB"',
    'CHROMADB_DIRECTORY = os.getenv("CHROMADB_DIRECTORY", "chromaDB")'
)

updated_content = updated_content.replace(
    'PROMPT_TEMPLATE_TXT = "prompt_template_memory.txt"',
    'PROMPT_TEMPLATE_TXT = os.getenv("PROMPT_TEMPLATE_TXT", "prompt_template_memory.txt")'
)

updated_content = updated_content.replace(
    'API_TYPE = "oneapi"',
    'API_TYPE = os.getenv("API_TYPE", "oneapi")'
)

updated_content = updated_content.replace(
    'OPENAI_API_BASE = "https://api.wlai.vip/v1"',
    'OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")'
)

updated_content = updated_content.replace(
    'OPENAI_CHAT_API_KEY = "sk-EhxvNWXkjzZJADfHA1Ac24Dd0f0b42B2B97f3725D3BcA378"',
    'OPENAI_CHAT_API_KEY = os.getenv("OPENAI_CHAT_API_KEY")'
)

updated_content = updated_content.replace(
    'OPENAI_CHAT_MODEL = "gpt-4o-mini"',
    'OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")'
)

updated_content = updated_content.replace(
    'OPENAI_EMBEDDING_API_KEY = "sk-EhxvNWXkjzZJADfHA1Ac24Dd0f0b42B2B97f3725D3BcA378"',
    'OPENAI_EMBEDDING_API_KEY = os.getenv("OPENAI_EMBEDDING_API_KEY")'
)

updated_content = updated_content.replace(
    'OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"',
    'OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")'
)

updated_content = updated_content.replace(
    'ONEAPI_API_BASE = "http://172.16.12.45:3000/v1"',
    'ONEAPI_API_BASE = os.getenv("ONEAPI_API_BASE")'
)

updated_content = updated_content.replace(
    'ONEAPI_CHAT_API_KEY = "sk-fS4eyjgqWJFK3U9z7fD01440262649A0A076A50859Cd5516"',
    'ONEAPI_CHAT_API_KEY = os.getenv("ONEAPI_CHAT_API_KEY")'
)

updated_content = updated_content.replace(
    'ONEAPI_CHAT_MODEL = "qwen-plus"',
    'ONEAPI_CHAT_MODEL = os.getenv("ONEAPI_CHAT_MODEL", "qwen-plus")'
)

updated_content = updated_content.replace(
    'ONEAPI_EMBEDDING_API_KEY = "sk-fS4eyjgqWJFK3U9z7fD01440262649A0A076A50859Cd5516"',
    'ONEAPI_EMBEDDING_API_KEY = os.getenv("ONEAPI_EMBEDDING_API_KEY")'
)

updated_content = updated_content.replace(
    'ONEAPI_EMBEDDING_MODEL = "text-embedding-v1"',
    'ONEAPI_EMBEDDING_MODEL = os.getenv("ONEAPI_EMBEDDING_MODEL", "text-embedding-v1")'
)

updated_content = updated_content.replace(
    'PORT = 8013',
    'PORT = int(os.getenv("PORT", 8013))'
)

# 写入更新后的内容
with open('mainMemory.py', 'w', encoding='utf-8') as f:
    f.write(updated_content)

print("mainMemory.py 已更新为使用环境变量配置")
