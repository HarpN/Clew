"""
reflective_job.py - Reflective Job & Model Performance Tracker
Background job that analyzes historical decision events logged in event_store,
aggregating execution performance, latency, and constraint metrics by model tier.
"""

import json
import logging
from typing import Dict, Any, List
import event_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clew.reflective_job")

def run_reflective_analysis(limit: int = 100) -> Dict[str, Any]:
    """
    Analyzes recent decision events and groups metrics by model tier.
    """
    events = event_store.get_events(limit=limit)
    
    tier_stats: Dict[str, Dict[str, Any]] = {}

    for event in events:
        meta = event.get("metadata", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        model = meta.get("model_used", "unknown_model")
        tier = meta.get("tier", "unknown_tier")
        event_type = event.get("event_type", "UNKNOWN")

        key = f"{tier} ({model})"
        if key not in tier_stats:
            tier_stats[key] = {
                "model_used": model,
                "tier": tier,
                "total_events": 0,
                "executed_count": 0,
                "blocked_count": 0,
                "domains_seen": set()
            }

        stats = tier_stats[key]
        stats["total_events"] += 1
        stats["domains_seen"].add(event.get("domain"))

        if event_type == "COMMAND_EXECUTED":
            stats["executed_count"] += 1
        elif event_type == "CONSTRAINT_BLOCKED":
            stats["blocked_count"] += 1

    # Format output dictionary
    report = {}
    for key, stats in tier_stats.items():
        total = stats["total_events"]
        exec_cnt = stats["executed_count"]
        block_cnt = stats["blocked_count"]
        success_rate = round((exec_cnt / total) * 100, 1) if total > 0 else 0.0

        report[key] = {
            "model_used": stats["model_used"],
            "tier": stats["tier"],
            "total_events": total,
            "executed": exec_cnt,
            "blocked": block_cnt,
            "success_rate_pct": success_rate,
            "domains": list(stats["domains_seen"])
        }

    logger.info(f"Reflective analysis complete. Analyzed {len(events)} events across {len(report)} model tiers.")
    return report

if __name__ == "__main__":
    summary = run_reflective_analysis()
    print(json.dumps(summary, indent=2))
