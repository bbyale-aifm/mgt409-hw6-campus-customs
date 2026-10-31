# Handbook Token Cost Estimate

## Result
- **File:** `shop_handbook.md` (28,903 characters)
- **Token count: 10,058**
- **Tokenizer:** `tiktoken` 0.14.0, via o200k_base (fallback: tiktoken has no entry for the model); the full file is encoded with `len(enc.encode(text))`.
- **Model priced:** `gpt-6-luna` (rates from `prices.json`, per 1M tokens)

| Rate | $ / 1M tokens |
|---|---|
| Input (uncached) | 0.1 |
| Cached input (cache read) | 0.01 |
| Cache write | 0.125 |
| Output | 0.5 (not used: only the handbook is sent as input here) |

## 1. Single call (uncached)
cost = tokens x input rate / 1,000,000
     = 10,058 x 0.1 / 1,000,000
     = **$0.001006**

## 2. 1,000 calls, no prompt caching
Every call pays the full input rate.
cost = 1 call cost x 1,000
     = $0.001006 x 1,000
     = **$1.005800**

## 3. 1,000 calls, with prompt caching on the handbook
The handbook is the same prefix on every call, so it can be cached. The first call writes the cache; the other 999 read it at the cached rate.

- Call 1 (cache write) = 10,058 x 0.125 / 1,000,000 = $0.001257
- Calls 2-1000 (cache reads) = 10,058 x 0.01 / 1,000,000 x 999 = $0.100479
- **Total = $0.001257 + $0.100479 = $0.101737**

If you ignore the one-time write fee and bill all 1,000 calls at the cached rate:
10,058 x 0.01 / 1,000,000 x 1,000 = $0.100580

## Comparison
| Scenario | Cost |
|---|---|
| 1 call, uncached | $0.001006 |
| 1,000 calls, uncached | $1.005800 |
| 1,000 calls, cached (1 write + 999 reads) | $0.101737 |
| Savings from caching | $0.904063 (89.9%) |

Note: these costs cover the handbook only. The question, document and model output are billed on top.
