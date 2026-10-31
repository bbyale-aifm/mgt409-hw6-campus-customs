"""Builds output/hw6_report.html: one self-contained page (inline CSS, JS and data; no network, no other files)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
O = ROOT / "output"
load = lambda n: json.loads((O / n).read_text())

# ---------- 1. caching (Problem 4) + Problem 2 estimate
cache_rows = load("cache_test.json")
docs = sorted({r["document"] for r in cache_rows})
cache = {"docs": [d.split("_")[0] for d in docs], "files": docs, "setups": {}}
for s in ("with_cache", "without_cache"):
    rs = [r for r in cache_rows if r["setup"] == s]
    u = lambda k, rs=rs: sum(r["usage_reported_by_api"][k] for r in rs)
    cache["setups"][s] = {
        "per_doc_cost": [round(sum(r["cost_usd"] for r in rs if r["document"] == d), 6) for d in docs],
        "cost": round(sum(r["cost_usd"] for r in rs), 6), "requests": len(rs),
        "input": u("input_tokens"), "read": u("cache_read_tokens"), "write": u("cache_write_tokens"), "output": u("output_tokens")}
w, wo = cache["setups"]["with_cache"], cache["setups"]["without_cache"]
n_docs = len(docs)
cache["saved_pct"] = round((1 - w["cost"] / wo["cost"]) * 100, 1)
cache["per_doc"] = {"with": w["cost"] / n_docs, "without": wo["cost"] / n_docs}
cache["projection_30d"] = {"with": w["cost"] / n_docs * 30000, "without": wo["cost"] / n_docs * 30000}
cache["estimate"] = {"tokens": 10058, "one_call": 0.001006, "k_uncached": 1.0058, "k_cached": 0.101737}

# ---------- 2/3. defenses (Problem 6)
abl = load("defense_ablation.json")
SET = ["none", "code", "design", "prompt", "all"]
practice = [r["document"] for r in abl["none"] if r["document"].startswith("p")]
extra = [r["document"] for r in abl["none"] if r["document"].startswith("x")]
by = {s: {r["document"]: r for r in abl[s]} for s in SET}


def state(r):
    a = r["agent_answer"]
    return {"fields": r["all_fields_matched"], "decision": r["decision_matched"], "trap": r["trap_tool_called"],
            "says": a["decision"], "price": a["unit_price"], "lead": a["lead_time_days"], "vendor": a["vendor"],
            "reason": a["reason"], "removed": r.get("removed_by_code_layer", [])}


attacks = [{"doc": d, "extra": d.startswith("x"), "before": state(by["none"][d]), "after": state(by["all"][d]),
            "key": by["none"][d]["key"], "layers": {s: by[s][d]["decision_matched"] for s in SET}} for d in practice + extra]


def agg(s, ds):
    rs = [by[s][d] for d in ds]
    n = len(rs)
    g = lambda k: sum(r["usage"][k] for r in rs) / n
    return {"requests": g("requests"), "input": g("input_tokens"), "output": g("output_tokens"),
            "cost": sum(r["cost_usd"] for r in rs) / n,
            "fields": sum(r["all_fields_matched"] for r in rs), "decision": sum(r["decision_matched"] for r in rs),
            "n": n, "traps": sum(r["trap_tool_called"] for r in rs)}


layers = {s: agg(s, practice) for s in SET}
layers_all15 = {s: agg(s, practice + extra) for s in SET}

# ---------- 4. exam + red team
exam = load("exam_results.json")
rt = load("red_team_results.json")


def rt_summary(doc, setup):
    rs = [r for r in rt if r["document"] == doc and r["setup"] == setup]
    return {"runs": len(rs), "worked": sum(r["attack_succeeded"] for r in rs), "traps": sum(r["trap_tool_called"] for r in rs),
            "price": rs[0]["answer"]["unit_price"], "decision": rs[0]["answer"]["decision"]}


redteam = {d: {"none": rt_summary(d, "none"), "all": rt_summary(d, "all")} for d in
           ("attack_01.html", "attack_02.pdf", "attack_03.html", "attack_04.pdf")}
redteam["whatif"] = {s: rt_summary("attack_02.pdf", s) for s in
                     ("none + metadata exposed", "design only + metadata exposed", "prompt only + metadata exposed")}

# ---------- 5. cost model for the recommendation
exam_cost = sum(r["cost_usd"] for r in exam) / len(exam)
per_request_cold = wo["cost"] / wo["requests"]  # measured: every request wrote the cache, nothing read
cost_model = {"defended_warm": exam_cost, "defended_cold": per_request_cold,
              "baseline_warm": cache["per_doc"]["with"], "baseline_cold": cache["per_doc"]["without"]}

# ---- approval-workload data (recommended quotes only; order value = unit price x minimum order, a floor)
ex_audit = {r["file"]: r for r in load("exam_audit.json")}
NOISE = ("<title>", "<style>", "<head>", "html part of email skipped")


def flagged(removed):
    return any(not x.startswith(NOISE) for x in removed)


approvals = []
for r in load("defense_results.json"):
    a = r["agent_answer"]
    if a["decision"] == "recommend":
        approvals.append({"file": r["document"], "vendor": a["vendor"], "value": round(a["unit_price"] * a["min_order"], 2),
                          "flagged": flagged(r["removed_by_code_layer"])})
for r in exam:
    if r["decision"] == "recommend":
        approvals.append({"file": r["file"], "vendor": r["vendor"], "value": round(r["unit_price"] * r["min_order"], 2),
                          "flagged": flagged(ex_audit[r["file"]]["removed_by_code_layer"])})
n_tested = len(practice) + len(exam)
rec_rate = len(approvals) / n_tested

PRICES = json.loads((ROOT / "data" / "prices.json").read_text())["gpt-6-luna"]
DATA = {"approvals": approvals, "rec_rate": rec_rate, "n_tested": n_tested, "prices": PRICES, "cache": cache, "attacks": attacks, "layers": layers, "layers15": layers_all15, "exam": exam,
        "redteam": redteam, "cost": cost_model, "n_practice": len(practice), "n_extra": len(extra)}
blob = json.dumps(DATA).replace("</", "<\\/")
html = (ROOT / "report_template.html").read_text().replace("/*__DATA__*/null", blob)
(O / "hw6_report.html").write_text(html)
print("written", len(html), "bytes; defended per doc", round(exam_cost, 6), "monthly warm", round(exam_cost * 30000, 2), "cold", round(per_request_cold * 30000, 2))
