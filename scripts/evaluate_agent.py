from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from novelops_agent.agent import build_agent
from novelops_agent.repository import JsonRepository


DATASET_PATH = ROOT / "seed_data" / "novelops_seed_50.json"
DEFAULT_REQUEST = "检查该作品的业务流程、合同与结算数据，识别异常并给出证据。"


def _safe_div(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


async def evaluate(
    limit: int | None = None, *, use_llm: bool = False
) -> dict[str, Any]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    novels = dataset["novels"][:limit]
    expected_by_novel = {
        row["novel_id"]: row for row in dataset["expected_anomalies"]
    }
    # Offline mode isolates deterministic Agent logic from API variance/cost;
    # --llm runs the real model (intent + plan + report) against the same gold set.
    if use_llm:
        app = build_agent(repo=JsonRepository(DATASET_PATH), enable_hybrid=False)
    else:
        app = build_agent(
            repo=JsonRepository(DATASET_PATH),
            model=False,
            enable_hybrid=False,
        )

    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for novel in novels:
        novel_id = novel["id"]
        expected_row = expected_by_novel.get(novel_id)
        expected_type = expected_row["anomaly_type"] if expected_row else "none"
        case_started = time.perf_counter()
        result = await app.ainvoke(
            {"request": DEFAULT_REQUEST, "novel_id": novel_id},
            config={"configurable": {"thread_id": f"eval-{novel_id}-{uuid.uuid4()}"}},
        )
        report = result.get("report", {})
        predicted_type = report.get("anomaly_type", "none")
        expected_positive = expected_type != "none"
        predicted_positive = predicted_type != "none"
        rows.append(
            {
                "novel_id": novel_id,
                "intent": result.get("intent", {}).get("intent"),
                "intent_source": result.get("intent", {}).get("source"),
                "expected": expected_type,
                "predicted": predicted_type,
                "exact_match": predicted_type == expected_type,
                "expected_positive": expected_positive,
                "predicted_positive": predicted_positive,
                "interrupt_expected": expected_positive,
                "interrupt_observed": "__interrupt__" in result,
                "evidence_count": len(report.get("evidence", [])),
                "latency_ms": round((time.perf_counter() - case_started) * 1000, 2),
            }
        )

    tp = sum(row["expected_positive"] and row["predicted_positive"] for row in rows)
    fp = sum(not row["expected_positive"] and row["predicted_positive"] for row in rows)
    fn = sum(row["expected_positive"] and not row["predicted_positive"] for row in rows)
    tn = sum(not row["expected_positive"] and not row["predicted_positive"] for row in rows)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0

    per_type_counts: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        per_type_counts[row["expected"]]["total"] += 1
        if row["exact_match"]:
            per_type_counts[row["expected"]]["correct"] += 1

    per_type = {
        anomaly_type: {
            "total": counts["total"],
            "correct": counts["correct"],
            "recall": _safe_div(counts["correct"], counts["total"]),
        }
        for anomaly_type, counts in sorted(per_type_counts.items())
    }
    intent_dist = Counter(row["intent"] for row in rows)
    intent_sources = Counter(row["intent_source"] for row in rows)
    return {
        "mode": "llm_full_chain" if use_llm else "offline_deterministic",
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "total_cases": len(rows),
        "metrics": {
            "exact_accuracy": _safe_div(sum(row["exact_match"] for row in rows), len(rows)),
            "binary_precision": precision,
            "binary_recall": recall,
            "binary_f1": f1,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "true_negative": tn,
            "interrupt_accuracy": _safe_div(
                sum(row["interrupt_expected"] == row["interrupt_observed"] for row in rows),
                len(rows),
            ),
            "evidence_coverage": _safe_div(
                sum(row["evidence_count"] > 0 for row in rows), len(rows)
            ),
            "total_latency_ms": round((time.perf_counter() - started) * 1000, 2),
        },
        "per_type": per_type,
        "intent_distribution": dict(intent_dist),
        "intent_sources": dict(intent_sources),
        "failures": [row for row in rows if not row["exact_match"]],
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NovelOps Agent业务评测")
    parser.add_argument("--limit", type=int, default=None, help="只评测前N个案例")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="使用真实大模型跑全链路（意图+规划+报告）；否则离线确定性",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(evaluate(args.limit, use_llm=args.llm)),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
