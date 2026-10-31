# Payment Approval Policy: Vendor Desk Agent

**For:** the owner. **Status:** proposed, to be confirmed by the owner. **Method:** daily batch for low-risk orders (option 2 in the report).

## 1. Who does what
- **Vendor desk agent:** reads vendor documents and *prepares* a recommendation. It can never pay, approve, or email. The defended agent has no such tools.
- **Store manager:** approves the daily batch and every one-off order.
- **Bookkeeper:** pays only orders a person has approved.
- **Owner:** sets and changes the limits below, and the approved vendor list (handbook section 4).

## 2. What an order needs to join the daily batch (all must be true)
1. Code, not the model, says all four handbook checks pass: approved vendor, price at or below the catalogue max, lead time 21 days or less, minimum order 600 units or less.
2. The defenses removed no hidden or instruction-like text from the document.
3. The document gives no conflicting prices, lead times or minimum orders.
4. The order total (unit price x minimum order) is under the **batch limit**: **less than $1,600**. Orders of $1,600 or above always need their own approval.
5. The day's batch total is under the **daily cap**.

## 3. Always approved one at a time
New or pending vendors. Orders of $1,600 or above. Any document the defenses flagged. Any order the agent marks `do_not_recommend` that a person wants to buy anyway.

## 4. Limits the owner sets
Based on the 9 orders the agent recommended in our 22 test documents (order value = unit price x minimum order, which is a floor, not the real total):

| Measure | All 9 orders | Clean 6 only |
|---|---|---|
| Median order value | $1,368.00 | $1,429.56 |
| Mean order value | $2,336.14 | $2,473.36 |
| Smallest / largest | $467.52 / $5,232.00 | $467.52 / $5,232.00 |

The mean is pulled up by two orders near $5,200, so the median is the better guide.

| Limit | Proposed start | Why |
|---|---|---|
| **Batch limit per order** | **$1,600** (set by the owner) | Just above the median ($1,368 all, $1,430 clean). On the test data it batches 3 of 9 recommended orders (33%): the clean orders at $468, $1,068 and $1,221. One clean order at $1,638 falls just above and needs its own approval. A $2,000 limit would batch 4 of 9 (44%). |
| **Daily batch cap** | Owner decides | I have no data to size this. Choose a total you would be comfortable losing on one bad day. |

The limit applies to the **order total**, not to each payment, so a large order cannot be split into small deposits or instalments to slip under $1,600. Several orders to the same vendor on the same day count together. These numbers come from a small sample and are starting points, not findings.

## 5. Rollout
1. **Month 1: approve every order by hand.** Record whether you agree with the agent on each one.
2. **Switch on batching** only when the owner is satisfied with the agreement rate.
3. **Stop switch:** if a batched order turns out wrong, batching stops and everything returns to one-at-a-time until the owner restarts it.

## 6. Ongoing checks
- Re-check a random slice of batched orders each week (suggested start: about 10%; not a measured figure).
- Keep the audit log (`audit_trail.json`) and review any `do_not_recommend` caused by conflicting numbers.
- Only the owner changes the limits, the vendor list, or this policy.

## 7. Known limits
- At 1,000 documents a day, about 41% of documents were recommended in testing, so roughly 409 orders a day. At the $1,600 limit about 136 orders a day would be batched and about 273 would still be one-offs. Even with no limit at all, the orders where the defenses removed hidden text (3 of 9) would still be one-offs, about 136 a day. If that is too many, add standing orders (option 3) for recurring reorders or plan for a lower volume.
- Known holes in the code layer (text hidden by CSS classes, and PDF text covered by a white box) can cause good quotes to be refused. Fix them before go-live.
