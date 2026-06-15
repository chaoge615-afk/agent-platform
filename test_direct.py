"""直接测试 LangGraph Agent（绕过 FastAPI 服务器）"""
import asyncio
import json
from src.agent.nodes import classify_intent

print("=" * 60)
print("直接测试 classify_intent 函数")
print("=" * 60)

# 测试 1: 结构化查询
print("\n测试 1: 结构化查询")
print("-" * 60)
result1 = asyncio.run(classify_intent({
    "question": "桃姐最近发了几个视频？",
    "conversation_id": None
}))
print(json.dumps(result1, indent=2, ensure_ascii=False))

# 测试 2: 语义查询
print("\n测试 2: 语义查询")
print("-" * 60)
result2 = asyncio.run(classify_intent({
    "question": "博主们对冷暴力怎么看？",
    "conversation_id": None
}))
print(json.dumps(result2, indent=2, ensure_ascii=False))

# 测试 3: 混合查询
print("\n测试 3: 混合查询")
print("-" * 60)
result3 = asyncio.run(classify_intent({
    "question": "桃姐最近聊了什么情感话题？她关于吵架的建议？",
    "conversation_id": None
}))
print(json.dumps(result3, indent=2, ensure_ascii=False))

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
