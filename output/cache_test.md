# Cache Test: with vs. without prompt caching

12 practice docs, each run in two setups with `gpt-6-luna`. Each doc takes **2 API requests** (one to read the file with a tool, one to return the answer), so 24 requests per setup. Every request is logged in `cache_test.json` with all API-reported token counts and its cost from `data/prices.json`.

## Setups
- **with_cache:** identical prompt prefix (instructions + handbook) on every request, plus a fixed `prompt_cache_key`.
- **without_cache:** a random request-id line is placed at the very top of the prompt on every request, so no request shares a prefix with any other and nothing can be read from cache.

## Check: do the API numbers match the setup?
- without_cache, `cache_read_tokens` = 0 on all 24 requests: **yes**.
- without_cache, `cache_write_tokens` = 0 on all requests: **NO**. The API reported **256,540 cache-write tokens** out of 259,564 input tokens.
- with_cache: 242,800 of 258,911 input tokens (93.8%) were read from cache; 13,087 were written.

So the no-reuse setup works (nothing was ever read from cache), but the "0 cached tokens" goal was only half met: see *Surprises* below.

## Cost

| Setup | Requests | Input tokens | Cache read | Cache write | Output tokens | Total cost | Per document |
|---|---|---|---|---|---|---|---|
| with_cache | 24 | 258,911 | 242,800 | 13,087 | 2,681 | $0.005709 | $0.000476 |
| without_cache | 24 | 259,564 | 0 | 256,540 | 2,772 | $0.033757 | $0.002813 |

**Saved by caching: $0.028048 (83.1%).**

### Cost per document

| Document | with_cache | without_cache | Saved |
|---|---|---|---|
| p01_bluehen_quote.html | $0.001591 | $0.002790 | 43.0% |
| p02_elmcity_quote.html | $0.000361 | $0.002809 | 87.1% |
| p03_ivyprint_catalog.html | $0.000419 | $0.002898 | 85.5% |
| p04_harborstitch_quote.html | $0.000372 | $0.002817 | 86.8% |
| p05_maplemills_quote.pdf | $0.000374 | $0.002802 | 86.7% |
| p06_qtextile_quote.pdf | $0.000367 | $0.002783 | 86.8% |
| p07_longwharf_quote.pdf | $0.000378 | $0.002817 | 86.6% |
| p08_chapelst_email.eml | $0.000359 | $0.002806 | 87.2% |
| p09_westville_email.eml | $0.000358 | $0.002804 | 87.2% |
| p10_eastrock_email.eml | $0.000374 | $0.002820 | 86.7% |
| p11_yorkst_quote.html | $0.000358 | $0.002792 | 87.2% |
| p12_bluehen_quote.pdf | $0.000398 | $0.002819 | 85.9% |

## Compared with the Problem 2 estimate

Problem 2 priced only the handbook (10,058 tokens) per call: $0.001006 uncached, $1.005800 for 1,000 uncached calls, and $0.101737 for 1,000 cached calls (1 write + 999 reads), a 89.9% saving.

| | Problem 2 estimate (handbook only, 1 call) | Real, per document (2 requests) |
|---|---|---|
| Uncached | $0.001006 | $0.002813 |
| Cached | $0.000102 | $0.000476 |
| Saving | 89.9% | 83.1% |

- The real cost per document is about 2.8x the estimate uncached and 4.7x cached. Reasons: each document needs **two requests**, so the handbook is billed twice; each request also carries the prompt, tool schemas and document text on top of the handbook; and output tokens are billed too.
- The saving (83.1%) is close to the estimated 89.9% because the handbook dominates the input. It is slightly lower because the real no-cache run was charged cache-write rates, not the plain input rate, and the with-cache run still wrote the cache once at the start.

## 30-day projection: 1,000 documents a day (30,000 documents)

Per-document averages from this test, scaled up. Assumes 2 requests per document and the same document sizes.

| Setup | Per document | Per day (1,000 docs) | 30 days (30,000 docs) |
|---|---|---|---|
| with_cache | $0.000476 | $0.48 | $14.27 |
| without_cache (as billed) | $0.002813 | $2.81 | $84.39 |
| **Difference** | $0.002337 | $2.34 | **$70.12** |

Caveat: at this volume the cache stays warm all day, so the with-cache figure is realistic. A cache that expires between sparse calls would cost more.

## Surprises

1. **The "uncached" run still had cache tokens, just writes instead of reads.** Even with a unique prefix on every request, the API reported 256,540 cache-write tokens (98.8% of input). This provider writes the cache automatically for any long prompt. I tried ways to turn that off (`prompt_cache_retention` set to `none` is rejected with a 400, `in_memory` is rejected for this model, `store=False`, the chat completions endpoint, and putting the handbook in the user message), and every one still showed cache writes. Reads can be prevented; writes cannot.
2. **No caching costs more than plain input.** Cache writes are billed at $0.125/1M, versus $0.1/1M for ordinary input. The no-cache run cost $0.033757; at the plain input rate it would have been $0.027342, so the write premium added $0.006415 (23.5%).
3. **Caching helps inside a single document.** Each document makes two requests with the same prefix, so the second one reads the handbook the first one wrote. In the with_cache run almost every request after the very first was a read.
4. **The first with_cache request paid full price.** Its cache was cold, so it wrote about 10,575 tokens at the write rate. After that, reads cost one tenth of the input rate. This is the one-time write fee the Problem 2 estimate included.
5. **Output was almost unchanged** between setups (2,681 vs 2,772 tokens), so the whole cost gap comes from how the handbook was billed.
