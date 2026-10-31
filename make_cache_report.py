"""Build output/cache_test.md from output/cache_test.json."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
rows = json.loads((ROOT / "output" / "cache_test.json").read_text())
P = json.loads((ROOT / "data" / "prices.json").read_text())["gpt-6-luna"]
SETUPS = ("with_cache", "without_cache")

per_doc = {s: defaultdict(lambda: defaultdict(float)) for s in SETUPS}
for r in rows:
    u, d = r["usage_reported_by_api"], per_doc[r["setup"]][r["document"]]
    d["requests"] += 1
    d["input"] += u["input_tokens"]; d["read"] += u["cache_read_tokens"]
    d["write"] += u["cache_write_tokens"]; d["output"] += u["output_tokens"]; d["cost"] += r["cost_usd"]
docs = sorted(per_doc["with_cache"])
tot = {s: {k: sum(per_doc[s][d][k] for d in docs) for k in ("requests", "input", "read", "write", "output", "cost")} for s in SETUPS}
w, wo = tot["with_cache"], tot["without_cache"]
saved = 1 - w["cost"] / wo["cost"]
n = len(docs)
avg_w, avg_wo = w["cost"] / n, wo["cost"] / n
plain_wo = (wo["input"] * P["input_per_1m"] + wo["output"] * P["output_per_1m"]) / 1e6  # if no write premium were charged
no_wo_read = all(r["usage_reported_by_api"]["cache_read_tokens"] == 0 for r in rows if r["setup"] == "without_cache")
no_wo_write = all(r["usage_reported_by_api"]["cache_write_tokens"] == 0 for r in rows if r["setup"] == "without_cache")
D = 30 * 1000
hb = 10058  # Problem 2 handbook token count
est_one, est_1000_nc, est_1000_c = 0.001006, 1.0058, 0.101737
f = lambda x: f"${x:,.6f}"

L = ["# Cache Test: with vs. without prompt caching", "",
     f"12 practice docs, each run in two setups with `gpt-6-luna`. Each doc takes **2 API requests** (one to read the file with a tool, one to return the answer), so {int(w['requests'])} requests per setup. "
     "Every request is logged in `cache_test.json` with all API-reported token counts and its cost from `data/prices.json`.", "",
     "## Setups",
     "- **with_cache:** identical prompt prefix (instructions + handbook) on every request, plus a fixed `prompt_cache_key`.",
     "- **without_cache:** a random request-id line is placed at the very top of the prompt on every request, so no request shares a prefix with any other and nothing can be read from cache.", "",
     "## Check: do the API numbers match the setup?",
     f"- without_cache, `cache_read_tokens` = 0 on all {int(wo['requests'])} requests: **{'yes' if no_wo_read else 'NO'}**.",
     f"- without_cache, `cache_write_tokens` = 0 on all requests: **{'yes' if no_wo_write else 'NO'}**. The API reported **{int(wo['write']):,} cache-write tokens** out of {int(wo['input']):,} input tokens.",
     f"- with_cache: {int(w['read']):,} of {int(w['input']):,} input tokens ({w['read'] / w['input']:.1%}) were read from cache; {int(w['write']):,} were written.", "",
     "So the no-reuse setup works (nothing was ever read from cache), but the \"0 cached tokens\" goal was only half met: see *Surprises* below.", "",
     "## Cost", "",
     "| Setup | Requests | Input tokens | Cache read | Cache write | Output tokens | Total cost | Per document |", "|---|---|---|---|---|---|---|---|"]
for s in SETUPS:
    t = tot[s]
    L.append(f"| {s} | {int(t['requests'])} | {int(t['input']):,} | {int(t['read']):,} | {int(t['write']):,} | {int(t['output']):,} | {f(t['cost'])} | {f(t['cost'] / n)} |")
L += ["", f"**Saved by caching: {f(wo['cost'] - w['cost'])} ({saved:.1%}).**", "",
      "### Cost per document", "", "| Document | with_cache | without_cache | Saved |", "|---|---|---|---|"]
for d in docs:
    a, b = per_doc["with_cache"][d]["cost"], per_doc["without_cache"][d]["cost"]
    L.append(f"| {d} | {f(a)} | {f(b)} | {1 - a / b:.1%} |")
L += ["", "## Compared with the Problem 2 estimate", "",
      f"Problem 2 priced only the handbook ({hb:,} tokens) per call: {f(est_one)} uncached, {f(est_1000_nc)} for 1,000 uncached calls, and {f(est_1000_c)} for 1,000 cached calls (1 write + 999 reads), a 89.9% saving.", "",
      "| | Problem 2 estimate (handbook only, 1 call) | Real, per document (2 requests) |", "|---|---|---|",
      f"| Uncached | {f(est_one)} | {f(avg_wo)} |", f"| Cached | {f(est_1000_c / 1000)} | {f(avg_w)} |",
      f"| Saving | 89.9% | {saved:.1%} |", "",
      f"- The real cost per document is about {avg_wo / est_one:.1f}x the estimate uncached and {avg_w / (est_1000_c / 1000):.1f}x cached. Reasons: each document needs **two requests**, so the handbook is billed twice; each request also carries the prompt, tool schemas and document text on top of the handbook; and output tokens are billed too.",
      f"- The saving ({saved:.1%}) is close to the estimated 89.9% because the handbook dominates the input. It is slightly lower because the real no-cache run was charged cache-write rates, not the plain input rate, and the with-cache run still wrote the cache once at the start.", "",
      "## 30-day projection: 1,000 documents a day (30,000 documents)", "",
      "Per-document averages from this test, scaled up. Assumes 2 requests per document and the same document sizes.", "",
      "| Setup | Per document | Per day (1,000 docs) | 30 days (30,000 docs) |", "|---|---|---|---|",
      f"| with_cache | {f(avg_w)} | ${avg_w * 1000:,.2f} | ${avg_w * D:,.2f} |",
      f"| without_cache (as billed) | {f(avg_wo)} | ${avg_wo * 1000:,.2f} | ${avg_wo * D:,.2f} |",
      f"| **Difference** | {f(avg_wo - avg_w)} | ${(avg_wo - avg_w) * 1000:,.2f} | **${(avg_wo - avg_w) * D:,.2f}** |", "",
      "Caveat: at this volume the cache stays warm all day, so the with-cache figure is realistic. A cache that expires between sparse calls would cost more.", "",
      "## Surprises", "",
      f"1. **The \"uncached\" run still had cache tokens, just writes instead of reads.** Even with a unique prefix on every request, the API reported {int(wo['write']):,} cache-write tokens ({wo['write'] / wo['input']:.1%} of input). This provider writes the cache automatically for any long prompt. I tried ways to turn that off (`prompt_cache_retention` set to `none` is rejected with a 400, `in_memory` is rejected for this model, `store=False`, the chat completions endpoint, and putting the handbook in the user message), and every one still showed cache writes. Reads can be prevented; writes cannot.",
      f"2. **No caching costs more than plain input.** Cache writes are billed at ${P['cache_write_per_1m']}/1M, versus ${P['input_per_1m']}/1M for ordinary input. The no-cache run cost {f(wo['cost'])}; at the plain input rate it would have been {f(plain_wo)}, so the write premium added {f(wo['cost'] - plain_wo)} ({wo['cost'] / plain_wo - 1:.1%}).",
      "3. **Caching helps inside a single document.** Each document makes two requests with the same prefix, so the second one reads the handbook the first one wrote. In the with_cache run almost every request after the very first was a read.",
      f"4. **The first with_cache request paid full price.** Its cache was cold, so it wrote about {int(rows[0]['usage_reported_by_api']['cache_write_tokens']):,} tokens at the write rate. After that, reads cost one tenth of the input rate. This is the one-time write fee the Problem 2 estimate included.",
      "5. **Output was almost unchanged** between setups (" + f"{int(w['output']):,} vs {int(wo['output']):,} tokens), so the whole cost gap comes from how the handbook was billed.", ""]
(ROOT / "output" / "cache_test.md").write_text("\n".join(L))
print("\n".join(L))
