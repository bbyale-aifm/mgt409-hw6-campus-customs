"""Defense layer 2 (design), part B: the decision is made by code, not by the model.

The model only extracts facts. This module re-checks them against the handbook tables and the document
text, then sets the decision itself. A document can therefore not talk the model into `recommend`.
"""
import re
from pathlib import Path

from models import RawFields, VendorQuote

HANDBOOK = (Path(__file__).resolve().parent / "data" / "shop_handbook.md").read_text(encoding="utf-8")
MAX_LEAD_DAYS, MAX_MIN_ORDER = 21, 600  # handbook section 4


def _table(heading: str) -> list[list[str]]:
    section = HANDBOOK.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in section.splitlines() if line.startswith("|")]
    return rows[2:]  # skip header and separator


APPROVED = {r[1].lower() for r in _table("## 5. Approved vendors")}
BLOCKED_NAMES = {r[0].lower(): r[0] for r in _table("## 6. Removed and pending vendors")}
BLOCKED = set(BLOCKED_NAMES)
MAX_COST = {r[0]: float(r[4].lstrip("$")) for r in _table("## 9. Product catalogue")}

PRICE = re.compile(r"price[^\n$]{0,60}\$\s?([\d,]+(?:\.\d+)?)", re.I)
LEAD = re.compile(r"lead[ -]time[^\n\d]{0,60}(\d+)", re.I)
MINORD = re.compile(r"minimum(?: order)?(?: quantity)?[^\n\d]{0,60}([\d,]+)", re.I)


def _nums(rx: re.Pattern, text: str) -> set[float]:
    return {float(m.replace(",", "")) for m in rx.findall(text)}


def _in_text(value: float | None, text: str) -> bool:
    if value is None:
        return True
    pool = {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text) if n.strip(",.")}
    return float(value) in pool


def check(q: RawFields, text: str) -> tuple[VendorQuote, list[str]]:
    """Build the final quote from the model's extracted facts. Decision and reason are computed here, in code."""
    problems: list[str] = []
    low = text.lower()

    for label, rx in (("unit price", PRICE), ("lead time", LEAD), ("minimum order", MINORD)):
        if len(_nums(rx, text)) > 1:
            problems.append(f"the document gives conflicting values for {label}")
    blocked = sorted(v for v in BLOCKED if v in low)
    if blocked:
        problems.append(f"the document names a removed or pending vendor ({BLOCKED_NAMES[blocked[0]]})")

    fields = {"unit price": q.unit_price, "lead time": q.lead_time_days, "minimum order": q.min_order}
    out = VendorQuote(**q.model_dump(), decision="do_not_recommend", reason="")
    for name, attr in (("unit price", "unit_price"), ("lead time", "lead_time_days"), ("minimum order", "min_order")):
        if not _in_text(fields[name], text):  # never keep a number the document does not contain
            setattr(out, attr, None)
            problems.append(f"{name} was not found in the document text")
        elif fields[name] is None and not any(name in p for p in problems):
            problems.append(f"{name} is missing")

    if q.vendor.lower() in BLOCKED and not blocked:
        problems.append(f"{q.vendor} is a removed or pending vendor")
    elif q.vendor.lower() not in APPROVED and q.vendor.lower() not in BLOCKED:
        problems.append(f"{q.vendor} is not an approved vendor")
    if q.vendor.lower() not in low:
        problems.append("the vendor name is not in the document")
    cap = MAX_COST.get(q.sku or "")
    if cap is None:
        problems.append("the SKU is not in the catalogue")
    elif out.unit_price is not None and out.unit_price > cap:
        problems.append(f"unit price ${out.unit_price:.2f} is above the catalogue max ${cap:.2f}")
    if out.lead_time_days is not None and out.lead_time_days > MAX_LEAD_DAYS:
        problems.append(f"lead time {out.lead_time_days} days is over {MAX_LEAD_DAYS}")
    if out.min_order is not None and out.min_order > MAX_MIN_ORDER:
        problems.append(f"minimum order {out.min_order} is over {MAX_MIN_ORDER}")

    out.decision = "do_not_recommend" if problems else "recommend"
    out.reason = ("Do not recommend: " + "; ".join(problems[:3])[0].upper() + "; ".join(problems[:3])[1:] + "."
                  if problems else "All four handbook checks pass: approved vendor, price, lead time and minimum order.")
    return out, problems
