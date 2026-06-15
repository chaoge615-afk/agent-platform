"""测试 Agent Platform API"""
import requests
import json

# 测试健康检查
print("=" * 50)
print("1. 健康检查")
print("=" * 50)
response = requests.get("http://localhost:8001/health")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# 测试聊天
print("\n" + "=" * 50)
print("2. 聊天测试")
print("=" * 50)
response = requests.post(
    "http://localhost:8001/api/chat",
    json={"question": "你好，请介绍一下自己"}
)
result = response.json()
print(f"问题: {result.get('answer', 'N/A')}")
print(f"路由类型: {result.get('route_type', 'N/A')}")
print(f"处理时间: {result.get('processing_time', 'N/A')}s")
print(f"错误: {result.get('error', '无')}")
