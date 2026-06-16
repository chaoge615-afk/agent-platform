"""A2A 协议测试

测试 A2A Server 和 Client 功能
"""
import asyncio
import httpx

from src.a2a.protocol import ROUTER_AGENT_CARD, MULTI_AGENT_PIPELINE_CARD
from src.a2a.client import A2AClient, A2AOrchestrator


async def test_agent_card():
    """测试获取 Agent Card"""
    print("测试: 获取 Agent Card")
    print(f"{'='*60}")

    client = A2AClient(ROUTER_AGENT_CARD)

    try:
        card = await client.get_agent_card()
        print(f"Agent ID: {card.id}")
        print(f"Name: {card.name}")
        print(f"Version: {card.version}")
        print(f"Description: {card.description}")
        print(f"\nCapabilities:")
        for cap in card.capabilities:
            print(f"  - {cap.name}: {cap.description}")
        print(f"\nEndpoint: {card.endpoint}")
        print(f"Metadata: {card.metadata}")
        print(f"{'='*60}\n")
        return True
    except Exception as e:
        print(f"错误: {e}\n")
        return False


async def test_create_task():
    """测试创建任务"""
    print("测试: 创建 A2A 任务")
    print(f"{'='*60}")

    client = A2AClient(ROUTER_AGENT_CARD)

    try:
        response = await client.create_task({
            "question": "有多少个UP主？",
            "conversation_id": "test-a2a",
        })

        print(f"Task ID: {response.task_id}")
        print(f"State: {response.state}")

        if response.output_data:
            print(f"\nAnswer:")
            print(f"{'-'*60}")
            print(response.output_data.get("answer", "无响应"))
            print(f"{'-'*60}")
            print(f"Route: {response.output_data.get('route_type')}")
            print(f"Sources: {len(response.output_data.get('sources', []))}")

        if response.error:
            print(f"Error: {response.error}")

        print(f"{'='*60}\n")
        return True

    except Exception as e:
        print(f"错误: {e}\n")
        return False


async def test_orchestrator():
    """测试编排器"""
    print("测试: A2A 编排器")
    print(f"{'='*60}")

    orchestrator = A2AOrchestrator()

    # 注册 Agent
    orchestrator.register_agent(ROUTER_AGENT_CARD)
    orchestrator.register_agent(MULTI_AGENT_PIPELINE_CARD)

    print(f"已注册 {len(orchestrator.clients)} 个 Agent")

    # 直接调用
    try:
        print(f"\n调用 Router Agent (LangGraph)...")
        response = await orchestrator.call_agent(
            ROUTER_AGENT_CARD.id,
            {"question": "总共采集了多少个视频？"},
        )
        print(f"  State: {response.state}")
        print(f"  Answer: {response.output_data.get('answer', '')[:100]}...")
    except Exception as e:
        print(f"  错误: {e}")

    print(f"{'='*60}\n")


async def main():
    """主函数"""
    print("\n" + "="*60)
    print("A2A 协议测试")
    print("="*60 + "\n")

    # 测试 1: Agent Card
    await test_agent_card()

    # 测试 2: 创建任务
    await test_create_task()

    # 测试 3: 编排器
    await test_orchestrator()


if __name__ == "__main__":
    asyncio.run(main())
