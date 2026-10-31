# Campus Customs Vendor Desk Agent (MGT 409, Homework 6)

An AI agent that reads vendor quotes, invoices, catalog pages and supplier emails (HTML, PDF and `.eml`), pulls out the vendor, SKU, unit price, lead time, minimum order, and recommends `recommend` or `do_not_recommend` under the Campus Customs shop handbook. This repo measures its cost, attacks it, defends it, and reports the results.

- **Model:** `gpt-6-luna` only, called through Portkey (PydanticAI, Responses API).
- **Safety:** the agent never sends email or makes payments. `send_email` and `approve_payment` are trap tools that only record an attempt in `output/trap_calls.json`.
- **Report:** open `output/hw6_report.html` by double-clicking it. It is one file and needs no internet.

## How to run the agent

Requires Python 3.10+ (developed on 3.13) and a Portkey API key.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then edit .env and put your key in PORTKEY_API_KEY
```

Run it on one document:

```bash
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

Choose the defenses with `--defense` (default `all`):

```bash
python agent.py --doc data/practice_docs/p02_elmcity_quote.html --defense none            # zero defenses (baseline)
python agent.py --doc data/practice_docs/p02_elmcity_quote.html --defense all             # code + design + prompt
python agent.py --doc data/practice_docs/p02_elmcity_quote.html --defense code,design     # any mix of code, design, prompt
```

Each run prints the structured answer and token usage, and appends to `output/usage_log.json` (API-reported tokens and dollar cost from `data/prices.json`) and `output/audit_trail.json` (tool calls and the final result). Never commit your real `.env`; it is listed in `.gitignore`.

## The three defense layers

1. **Code** (`sanitize.py`): rebuilds the document as a person would see it, dropping hidden, tiny, white, off-screen or off-page text, comments, hidden links and invisible Unicode, and lines that give orders to an AI.
2. **Design** (`policy.py`): the model gets no tools and extracts only five facts; Python applies the handbook rules and makes the decision.
3. **Prompt** (`prompts/prompt.md`): strict rules to treat the document as data and ignore embedded instructions. The original prompt is kept as `prompts/prompt_baseline.md` for the zero-defense mode.

## Reproducing each problem

| Problem | Command | Output |
|---|---|---|
| 2 Handbook cost | `python estimate_handbook.py` | `output/handbook_estimate.md` |
| 3 Build the agent | `python agent.py --doc ...` | `output/usage_log.json`, `audit_trail.json`, `harness.md` |
| 4 Cache test | `python cache_test.py` then `python make_cache_report.py` | `output/cache_test.json`, `cache_test.md` |
| 5 Attack | `python attack_test.py` | `output/attack_results.json`, `attack_results.md` |
| 6 Defend | `python defense_test.py` then `python make_defense_report.py` | `output/defense_results.json`, `defense_results.md`, `defense_ablation.json` |
| 7 Red team | `python make_my_attacks.py` then `python red_team_test.py` | `data/my_attacks/`, `output/red_team.md`, `red_team_results.json` |
| 8 Exam | `python exam_run.py` | `output/exam_results.json`, `exam_audit.json` |
| 9 Report page | `python build_report.py` | `output/hw6_report.html` |

The scripts call the model, so they need your `.env` and cost a small amount (the whole project cost well under a dollar).

## Key results

| Measure | Result |
|---|---|
| Handbook size | 10,058 tokens |
| Caching saving (12 practice docs) | 83.1% ($0.005709 with cache vs $0.033757 without) |
| Practice docs fully right | 8/12 with no defenses, 12/12 with all three defenses |
| Trap tool calls | 0 in every test run |
| Defended cost | about $0.0002 per document, about $5.87 a month at 1,000 documents a day |

## Repository layout

```
AI_prompts.md        log of the prompts used to build this
README.md            this file
.env.example         placeholder for PORTKEY_API_KEY (copy to .env)
agent.py tools.py models.py   the agent, its tools and its output models
sanitize.py policy.py         defense layers 1 and 2
prompts/             prompt.md (strict) and prompt_baseline.md
data/                course data: handbook, prices, practice docs and key, exam docs
  my_attacks/        red-team files (attack_01 and attack_02 as assigned, plus two extras)
  extra_attacks/     three extra visible-text attacks used in Problem 6
output/              every result, report and log
*_test.py, make_*.py, build_report.py, report_template.html, exam_run.py   scripts that produce the outputs
```

## Known limits

The code layer does not read CSS rules in `<style>` blocks and cannot see PDF text covered by a white box, so two of my extra attacks turn good quotes into false refusals (safe, but costly). See `output/red_team.md`. A proposed approval policy for payments is in `output/approval_policy.md`.
