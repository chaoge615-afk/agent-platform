"""自动化评估脚本

评估维度：
1. 路由准确率（意图分类是否正确）
2. 响应时间（端到端延迟）
3. Token 消耗（LLM 调用成本）

使用方法：
    python -m tests.evaluator

输出：
    - 控制台报告
    - JSON 报告（tests/evaluation_report.json）
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

from tests.test_cases import get_test_cases, get_stats


class AgentEvaluator:
    """Agent 评估器"""

    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
        self.results = []

    async def evaluate_single(self, test_case: dict, verbose: bool = True) -> dict:
        """评估单个测试用例

        Args:
            test_case: 测试用例
            verbose: 是否打印详细信息

        Returns:
            dict: 评估结果
        """
        question = test_case["question"]
        expected_route = test_case["expected_route"]

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/chat",
                    json={"question": question},
                )
                response.raise_for_status()
                result = response.json()

            elapsed = time.time() - start_time

            # 判断路由是否正确
            actual_route = result.get("route_type", "unknown")
            route_correct = actual_route == expected_route

            # 提取关键信息
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            eval_result = {
                "question": question,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "route_correct": route_correct,
                "elapsed_time": round(elapsed, 2),
                "answer": answer,
                "sources": sources,
                "error": None,
            }

            if verbose:
                status = "[OK]" if route_correct else "[FAIL]"
                print(f"{status} [{elapsed:.2f}s] {question[:30]}...")
                print(f"  期望: {expected_route} | 实际: {actual_route}")

            return eval_result

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "question": question,
                "expected_route": expected_route,
                "actual_route": "error",
                "route_correct": False,
                "elapsed_time": round(elapsed, 2),
                "answer": "",
                "sources": [],
                "error": str(e),
            }

    async def evaluate_batch(
        self,
        route_type: Optional[str] = None,
        difficulty: Optional[str] = None,
        max_cases: Optional[int] = None,
        verbose: bool = True,
    ) -> list[dict]:
        """批量评估测试用例

        Args:
            route_type: 筛选路由类型
            difficulty: 筛选难度
            max_cases: 最大用例数
            verbose: 是否打印详细信息

        Returns:
            list: 评估结果列表
        """
        test_cases = get_test_cases(route_type=route_type, difficulty=difficulty)

        if max_cases:
            test_cases = test_cases[:max_cases]

        if verbose:
            stats = get_stats()
            print(f"\n{'='*60}")
            print(f"Agent Evaluation Report")
            print(f"{'='*60}")
            print(f"Test cases: {len(test_cases)}/{stats['total']}")
            print(f"{'='*60}\n")

        results = []
        for i, test_case in enumerate(test_cases, 1):
            if verbose:
                print(f"[{i}/{len(test_cases)}] ", end="")

            result = await self.evaluate_single(test_case, verbose=verbose)
            results.append(result)

            # 避免请求过快
            await asyncio.sleep(0.5)

        self.results = results
        return results

    def generate_report(self, output_path: str = "tests/evaluation_report.json"):
        """生成评估报告

        Args:
            output_path: 输出路径
        """
        if not self.results:
            print("错误: 没有评估结果")
            return

        # 统计
        total = len(self.results)
        correct = sum(1 for r in self.results if r["route_correct"])
        errors = sum(1 for r in self.results if r["error"])
        avg_time = sum(r["elapsed_time"] for r in self.results) / total

        # 按路由类型统计
        route_stats = {}
        for r in self.results:
            expected = r["expected_route"]
            if expected not in route_stats:
                route_stats[expected] = {"total": 0, "correct": 0}
            route_stats[expected]["total"] += 1
            if r["route_correct"]:
                route_stats[expected]["correct"] += 1

        # 计算准确率
        accuracy = correct / total * 100
        route_accuracy = {
            route: f"{stats['correct']}/{stats['total']} ({stats['correct']/stats['total']*100:.1f}%)"
            for route, stats in route_stats.items()
        }

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_cases": total,
                "correct_routes": correct,
                "errors": errors,
                "accuracy": f"{accuracy:.2f}%",
                "avg_response_time": f"{avg_time:.2f}s",
            },
            "route_accuracy": route_accuracy,
            "failed_cases": [
                {
                    "question": r["question"],
                    "expected": r["expected_route"],
                    "actual": r["actual_route"],
                    "error": r["error"],
                }
                for r in self.results
                if not r["route_correct"]
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
        print(f"Evaluation Report")
        print(f"{'='*60}")
        print(f"Time: {report['timestamp']}")
        print(f"{'='*60}\n")

        print("Summary:")
        print(f"  Test cases: {total}")
        print(f"  Correct routes: {correct}/{total}")
        print(f"  Accuracy: {accuracy:.2f}%")
        print(f"  Errors: {errors}")
        print(f"  Avg response time: {avg_time:.2f}s\n")

        print("Route accuracy:")
        for route, acc in route_accuracy.items():
            print(f"  {route}: {acc}")
        print()

        if report["failed_cases"]:
            print(f"Failed cases ({len(report['failed_cases'])}):")
            for i, case in enumerate(report["failed_cases"][:10], 1):
                print(f"  {i}. {case['question'][:40]}...")
                print(f"     Expected: {case['expected']} | Actual: {case['actual']}")
                if case["error"]:
                    print(f"     Error: {case['error']}")
            if len(report["failed_cases"]) > 10:
                print(f"  ... and {len(report['failed_cases']) - 10} more failed cases")
            print()

        print(f"Detailed report saved to: {output_file}")
        print(f"{'='*60}\n")

        return report


async def main():
    """主函数"""
    evaluator = AgentEvaluator()

    # 评估所有测试用例
    await evaluator.evaluate_batch(verbose=True)

    # 生成报告
    evaluator.generate_report()


if __name__ == "__main__":
    asyncio.run(main())
