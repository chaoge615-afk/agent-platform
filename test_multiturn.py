"""测试多轮对话（Checkpoint 持久化）"""
import requests
import json
import uuid

API_BASE = "http://localhost:8001"

print("=" * 60)
print("多轮对话测试（Checkpoint 持久化）")
print("=" * 60)

# 生成唯一的 conversation_id
conversation_id = str(uuid.uuid4())
print(f"\n对话 ID: {conversation_id}\n")

# 第一轮对话
print("-" * 60)
print("第 1 轮: 桃姐最近发了几个视频？")
print("-" * 60)
response1 = requests.post(
    f"{API_BASE}/api/chat",
    json={
        "question": "桃姐最近发了几个视频？",
        "conversation_id": conversation_id
    }
)
result1 = response1.json()
print(f"路由类型: {result1.get('route_type', 'N/A')}")
print(f"回答: {result1.get('answer', 'N/A')[:100]}...")
print(f"处理时间: {result1.get('processing_time', 'N/A')}s")

# 第二轮对话（测试上下文保持）
print("\n" + "-" * 60)
print("第 2 轮: 她呢？（测试指代解析）")
print("-" * 60)
response2 = requests.post(
    f"{API_BASE}/api/chat",
    json={
        "question": "她呢？",
        "conversation_id": conversation_id
    }
)
result2 = response2.json()
print(f"路由类型: {result2.get('route_type', 'N/A')}")
print(f"回答: {result2.get('answer', 'N/A')[:100]}...")
print(f"处理时间: {result2.get('processing_time', 'N/A')}s")

# 第三轮对话（测试新话题）
print("\n" + "-" * 60)
print("第 3 轮: 博主们对冷暴力怎么看？")
print("-" * 60)
response3 = requests.post(
    f"{API_BASE}/api/chat",
    json={
        "question": "博主们对冷暴力怎么看？",
        "conversation_id": conversation_id
    }
)
result3 = response3.json()
print(f"路由类型: {result3.get('route_type', 'N/A')}")
print(f"回答: {result3.get('answer', 'N/A')[:100]}...")
print(f"处理时间: {result3.get('processing_time', 'N/A')}s")

# 检查对话历史
print("\n" + "=" * 60)
print("检查对话历史")
print("=" * 60)
history_response = requests.get(f"{API_BASE}/api/threads/{conversation_id}/history")
history = history_response.json()

print(f"线程 ID: {history.get('thread_id')}")
print(f"对话轮数: {len(history.get('history', []))}")

for i, turn in enumerate(history.get("history", []), 1):
    print(f"\n第 {i} 轮:")
    print(f"  问题: {turn.get('question', 'N/A')}")
    print(f"  路由: {turn.get('route_type', 'N/A')}")
    print(f"  时间: {turn.get('timestamp', 'N/A')}")

# 列出所有线程
print("\n" + "=" * 60)
print("列出所有对话线程")
print("=" * 60)
threads_response = requests.get(f"{API_BASE}/api/threads")
threads = threads_response.json()

print(f"总线程数: {len(threads.get('threads', []))}")
for thread in threads.get("threads", []):
    print(f"  - {thread}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
