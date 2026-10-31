"""Token count and dollar cost of sending the shop handbook as input to gpt-6-luna."""
import json
from decimal import Decimal
from pathlib import Path

import tiktoken

MODEL = "gpt-6-luna"
HERE = Path(__file__).parent
DATA = HERE / "data" if (HERE / "data" / "shop_handbook.md").exists() else HERE
OUT = HERE / "output" / "handbook_estimate.md"
CALLS = 1000

text = (DATA / "shop_handbook.md").read_text(encoding="utf-8")
try:
    enc, how = tiktoken.encoding_for_model(MODEL), f"encoding_for_model('{MODEL}')"
except KeyError:  # tiktoken does not know this model name yet
    enc, how = tiktoken.get_encoding("o200k_base"), "o200k_base (fallback: tiktoken has no entry for the model)"
tokens = len(enc.encode(text))

p = json.loads((DATA / "prices.json").read_text())[MODEL]
inp, cached, write, out = (Decimal(str(p[k])) for k in
                           ("input_per_1m", "cached_input_per_1m", "cache_write_per_1m", "output_per_1m"))
M = Decimal(1_000_000)
T = Decimal(tokens)

one = T * inp / M
no_cache = one * CALLS
all_cached = T * cached / M * CALLS                      # every call billed at the cached rate
first = T * write / M                                    # call 1 writes the cache
rest = T * cached / M * (CALLS - 1)                      # calls 2..1000 read it
with_cache = first + rest


def d(x): return f"${x:,.6f}"


md = f"""# Handbook Token Cost Estimate

## Result
- **File:** `shop_handbook.md` ({len(text):,} characters)
- **Token count: {tokens:,}**
- **Tokenizer:** `tiktoken` {tiktoken.__version__}, via {how}; the full file is encoded with `len(enc.encode(text))`.
- **Model priced:** `{MODEL}` (rates from `prices.json`, per 1M tokens)

| Rate | $ / 1M tokens |
|---|---|
| Input (uncached) | {inp} |
| Cached input (cache read) | {cached} |
| Cache write | {write} |
| Output | {out} (not used: only the handbook is sent as input here) |

## 1. Single call (uncached)
cost = tokens x input rate / 1,000,000
     = {tokens:,} x {inp} / 1,000,000
     = **{d(one)}**

## 2. 1,000 calls, no prompt caching
Every call pays the full input rate.
cost = 1 call cost x 1,000
     = {d(one)} x 1,000
     = **{d(no_cache)}**

## 3. 1,000 calls, with prompt caching on the handbook
The handbook is the same prefix on every call, so it can be cached. The first call writes the cache; the other 999 read it at the cached rate.

- Call 1 (cache write) = {tokens:,} x {write} / 1,000,000 = {d(first)}
- Calls 2-1000 (cache reads) = {tokens:,} x {cached} / 1,000,000 x 999 = {d(rest)}
- **Total = {d(first)} + {d(rest)} = {d(with_cache)}**

If you ignore the one-time write fee and bill all 1,000 calls at the cached rate:
{tokens:,} x {cached} / 1,000,000 x 1,000 = {d(all_cached)}

## Comparison
| Scenario | Cost |
|---|---|
| 1 call, uncached | {d(one)} |
| 1,000 calls, uncached | {d(no_cache)} |
| 1,000 calls, cached (1 write + 999 reads) | {d(with_cache)} |
| Savings from caching | {d(no_cache - with_cache)} ({(1 - with_cache / no_cache) * 100:.1f}%) |

Note: these costs cover the handbook only. The question, document and model output are billed on top.
"""
OUT.write_text(md)
print(md)
