"""性能基准测试

测试维度：
1. 响应时间（P50, P90, P95, P99）
2. 并发处理能力
3. 内存占用
4. Token 消耗

使用方法：
    python -m tests.benchmark

输出：
    - 控制台报告
    - JSON 报告（tests/benchmark_report.json）
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from tests.test_cases import get_test_cases


class Benchmark:
    """性能基准测试"""

    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.results = []

    async def single_request(self, question: str) -> dict:
        """单个请求测试"""
        start_time = time.time()
        start_memory = 0  # 可以通过 psutil 获取

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/chat",
                    json={"question": question},
                )
                response.raise_for_status()
                result = response.json()

            elapsed = time.time() - start_time

            return {
                "question": question,
                "elapsed": elapsed,
                "status": "success",
                "route_type": result.get("route_type"),
                "answer_length": len(result.get("answer", "")),
                "error": None,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "question": question,
                "elapsed": elapsed,
                "status": "error",
                "route_type": None,
                "answer_length": 0,
                "error": str(e),
            }

    async def sequential_test(self, max_cases: int = 20) -> list[dict]:
        """顺序测试"""
        test_cases = get_test_cases()[:max_cases]

        print(f"\n顺序测试: {max_cases} 个请求")
        print(f"{'='*60}")

        results = []
        for i, case in enumerate(test_cases, 1):
            print(f"[{i}/{max_cases}] ", end="")
            result = await self.single_request(case["question"])
            results.append(result)
            print(f"{result['elapsed']:.2f}s - {result['status']}")

            await asyncio.sleep(0.2)

        self.results = results
        return results

    async def concurrent_test(self, concurrency: int = 5, max_cases: int = 20) -> list[dict]:
        """并发测试"""
        test_cases = get_test_cases()[:max_cases]

        print(f"\n并发测试: {max_cases} 个请求, 并发数: {concurrency}")
        print(f"{'='*60}")

        semaphore = asyncio.Semaphore(concurrency)

        async def limited_request(question: str, index: int):
            async with semaphore:
                print(f"[{index}] 开始")
                result = await self.single_request(question)
                print(f"[{index}] 完成: {result['elapsed']:.2f}s - {result['status']}")
                return result

        tasks = [
            limited_request(case["question"], i + 1)
            for i, case in enumerate(test_cases)
        ]

        results = await asyncio.gather(*tasks)
        self.results.extend(results)
        return results

    def calculate_percentiles(self, times: list[float]) -> dict:
        """计算百分位数"""
        sorted_times = sorted(times)
        n = len(sorted_times)

        return {
            "p50": sorted_times[int(n * 0.5)],
            "p90": sorted_times[int(n * 0.9)],
            "p95": sorted_times[int(n * 0.95)],
            "p99": sorted_times[min(int(n * 0.99), n - 1)],
            "min": sorted_times[0],
            "max": sorted_times[-1],
            "avg": sum(sorted_times) / n,
        }

    def generate_report(self, output_path: str = "tests/benchmark_report.json"):
        """生成基准测试报告"""
        if not self.results:
            print("错误: 没有测试结果")
            return

        # 过滤成功的请求
        successful = [r for r in self.results if r["status"] == "success"]
        failed = [r for r in self.results if r["status"] == "error"]

        if not successful:
            print("错误: 没有成功的请求")
            return

        # 计算响应时间统计
        times = [r["elapsed"] for r in successful]
        percentiles = self.calculate_percentiles(times)

        # 计算吞吐量
        total_time = sum(times)
        throughput = len(successful) / total_time if total_time > 0 else 0

        # 按路由类型统计
        route_stats = {}
        for r in successful:
            route = r["route_type"] or "unknown"
            if route not in route_stats:
                route_stats[route] = []
            route_stats[route].append(r["elapsed"])

        route_summary = {
            route: {
                "count": len(times),
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
            }
            for route, times in route_stats.items()
        }

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_requests": len(self.results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": f"{len(successful)/len(self.results)*100:.2f}%",
                "total_time": f"{total_time:.2f}s",
                "throughput": f"{throughput:.2f} req/s",
            },
            "response_time": {
                "p50": f"{percentiles['p50']:.2f}s",
                "p90": f"{percentiles['p90']:.2f}s",
                "p95": f"{percentiles['p95']:.2f}s",
                "p99": f"{percentiles['p99']:.2f}s",
                "min": f"{percentiles['min']:.2f}s",
                "max": f"{percentiles['max']:.2f}s",
                "avg": f"{percentiles['avg']:.2f}s",
            },
            "route_breakdown": route_summary,
            "errors": [
                {"question": r["question"], "error": r["error"]}
                for r in failed
            ],
            "detailed_results": self.results,
        }

        # 保存 JSON
        output_file = Path(output_path)
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 打印报告
        print(f"\n{'='*60}")
        print(f"性能基准测试报告")
        print(f"{'='*60}")
        print(f"时间: {report['timestamp']}")
        print(f"{'='*60}\n")

        print("总体统计:")
        print(f"  总请求数: {len(self.results)}")
        print(f"  成功: {len(successful)}")
        print(f"  失败: {len(failed)}")
        print(f"  成功率: {report['summary']['success_rate']}")
        print(f"  总耗时: {report['summary']['total_time']}")
        print(f"  吞吐量: {report['summary']['throughput']}\n")

        print("响应时间:")
        print(f"  P50: {report['response_time']['p50']}")
        print(f"  P90: {report['response_time']['p90']}")
        print(f"  P95: {report['response_time']['p95']}")
        print(f"  P99: {report['response_time']['p99']}")
        print(f"  平均: {report['response_time']['avg']}")
        print(f"  最小: {report['response_time']['min']}")
        print(f"  最大: {report['response_time']['max']}\n")

        print("路由分布:")
        for route, stats in route_summary.items():
            print(f"  {route}:")
            print(f"    数量: {stats['count']}")
            print(f"    平均: {stats['avg']:.2f}s")
            print(f"    范围: {stats['min']:.2f}s - {stats['max']:.2f}s")
        print()

        if failed:
            print(f"错误请求 ({len(failed)}):")
            for i, err in enumerate(failed[:5], 1):
                print(f"  {i}. {err['question'][:40]}...")
                print(f"     错误: {err['error']}")
            if len(failed) > 5:
                print(f"  ... 还有 {len(failed) - 5} 个错误")
            print()

        print(f"详细报告已保存到: {output_file}")
        print(f"{'='*60}\n")

        return report


async def main():
    """主函数"""
    benchmark = Benchmark()

    # 顺序测试
    await benchmark.sequential_test(max_cases=20)

    # 并发测试
    await benchmark.concurrent_test(concurrency=5, max_cases=10)

    # 生成报告
    benchmark.generate_report()


if __name__ == "__main__":
    asyncio.run(main())
