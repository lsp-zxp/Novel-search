from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid

from langgraph.types import Command

from novelops_agent.agent import build_agent


def _print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


async def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NovelOps 异常调查 Agent")
    parser.add_argument("--novel-id", default="N001")
    parser.add_argument(
        "--request",
        default="调查《长夜回声》为什么结算金额可能不正确",
    )
    parser.add_argument(
        "--approve",
        choices=["ask", "yes", "no"],
        default="ask",
        help="工单审批方式；CI或演示可使用 yes/no",
    )
    args = parser.parse_args()

    app = build_agent()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = await app.ainvoke(
        {"request": args.request, "novel_id": args.novel_id},
        config=config,
    )

    print("\n=== 意图识别 ===")
    _print_json(result.get("intent", {}))
    print("\n=== 执行计划 ===")
    _print_json(result.get("plan", []))

    print("\n=== 调查报告 ===")
    _print_json(result.get("report", {}))

    if "__interrupt__" not in result:
        return

    if args.approve == "ask":
        answer = input("\n发现异常，是否创建工单？[y/N] ").strip().lower()
        approved = answer in {"y", "yes"}
    else:
        approved = args.approve == "yes"

    final = await app.ainvoke(
        Command(resume={"approved": approved, "reviewer": "cli_user"}),
        config=config,
    )
    print("\n=== 审批结果 ===")
    _print_json(final.get("case", {"status": "rejected"}))


if __name__ == "__main__":
    asyncio.run(main())
