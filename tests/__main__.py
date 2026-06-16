"""测试运行器

快速运行测试：
    # 运行单个测试
    python -m tests.test_single "有多少个UP主？"

    # 运行评估
    python -m tests.evaluator

    # 运行基准测试
    python -m tests.benchmark

    # 测试 SSE 流式输出
    python -m tests.test_stream "桃姐最近讲了什么？"
"""
import asyncio
import sys

import httpx


async def test_single(question: str):
    """测试单个问题"""
    print(f"问题: {question}")
    print(f"{'='*60}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            start = asyncio.get_event_loop().time()
            response = await client.post(
                "http://localhost:8001/api/chat",
                json={"question": question},
            )
            elapsed = asyncio.get_event_loop().time() - start

            response.raise_for_status()
            result = response.json()

            print(f"\n回答:")
            print(f"{'-'*60}")
            print(result.get("answer", "无响应"))
            print(f"{'-'*60}")

            print(f"\n元信息:")
            print(f"  路由: {result.get('route_type')}")
            print(f"  耗时: {elapsed:.2f}s")
            print(f"  来源: {len(result.get('sources', []))} 个")

            if result.get("error"):
                print(f"  错误: {result.get('error')}")

    except httpx.ConnectError:
        print("\n错误: 无法连接到 Agent Platform")
        print("请确保服务已启动: python -m src.main")
    except Exception as e:
        print(f"\n错误: {e}")


async def test_stream(question: str):
    """测试 SSE 流式输出"""
    print(f"问题: {question}")
    print(f"{'='*60}")
    print(f"\n流式输出:")
    print(f"{'-'*60}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "http://localhost:8001/api/chat/stream",
                json={"question": question},
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        event = line[7:]
                        print(f"\n[事件: {event}]")
                    elif line.startswith("data: "):
                        import json
                        data = json.loads(line[6:])
                        print(f"  数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

        print(f"\n{'-'*60}")
        print("流式输出完成")

    except httpx.ConnectError:
        print("\n错误: 无法连接到 Agent Platform")
        print("请确保服务已启动: python -m src.main")
    except Exception as e:
        print(f"\n错误: {e}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]

    if command == "test_single" and len(sys.argv) >= 3:
        question = " ".join(sys.argv[2:])
        asyncio.run(test_single(question))

    elif command == "test_stream" and len(sys.argv) >= 3:
        question = " ".join(sys.argv[2:])
        asyncio.run(test_stream(question))

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
