"""Run all practice docs with and without prompt caching. Logs every API request to output/cache_test.json."""
import dataclasses
import json
from datetime import datetime, timezone

from pydantic_ai.messages import ModelResponse
from pydantic_ai.usage import UsageLimits

import agent

DOCS = sorted((agent.ROOT / "data" / "practice_docs").iterdir())
OUT = agent.ROOT / "output" / "cache_test.json"


def run_setup(setup: str, rows: list) -> None:
    ag = agent.build_agent(cache=(setup == "with_cache"))
    for doc in DOCS:
        run = ag.run_sync(f"Process this vendor document: {doc}", usage_limits=UsageLimits(request_limit=12))
        calls = [m for m in run.new_messages() if isinstance(m, ModelResponse)]
        for i, m in enumerate(calls, 1):
            cost = agent.cost_usd(m.usage)
            rows.append({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "setup": setup,
                         "document": doc.name, "request_index": i, "model": agent.MODEL,
                         "usage_reported_by_api": dataclasses.asdict(m.usage), "cost_usd": cost["cost_usd"]})
        print(setup, doc.name, run.output.decision, flush=True)


rows: list = []
run_setup("with_cache", rows)
run_setup("without_cache", rows)
OUT.write_text(json.dumps(rows, indent=2))

bad = [r for r in rows if r["setup"] == "without_cache" and
       (r["usage_reported_by_api"]["cache_read_tokens"] or r["usage_reported_by_api"]["cache_write_tokens"])]
print(f"{len(rows)} requests logged; without_cache requests showing cached/written tokens: {len(bad)}")
