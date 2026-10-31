"""Problem 8: run the defended agent (all three layers) on every file in data/exam_docs/. No hand-editing of results."""
import json

import agent
import tools
from defense_test import traps

ROOT = agent.ROOT
DOCS = sorted((ROOT / "data" / "exam_docs").iterdir())
LAYERS = agent.parse_layers("all")

results, audit = [], []
for doc in DOCS:
    before = len(traps())
    r = agent.run_document(str(doc), LAYERS)
    q, u = r["result"], r["usage"]
    results.append({
        "file": doc.name,
        "vendor": q.vendor, "sku": q.sku, "unit_price": q.unit_price,
        "lead_time_days": q.lead_time_days, "min_order": q.min_order,
        "decision": q.decision, "reason": q.reason,
        "trap_tool_called": len(traps()) > before,
        "input_tokens": u["input_tokens"], "cached_tokens": u["cached_input_tokens"],
        "output_tokens": u["output_tokens"], "cost_usd": u["cost_usd"],
    })
    audit.append({"file": doc.name, "removed_by_code_layer": r["removed"], "policy_notes": r["policy_notes"],
                  "model_extraction": r["model_answer"].model_dump(), "cache_write_tokens": u["cache_write_tokens"],
                  "requests": u["requests"], "text_the_model_read": r["text_read"]})
    print(doc.name, q.decision, flush=True)
(ROOT / "output" / "exam_results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
(ROOT / "output" / "exam_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False))
print("done")
