# Fewer empty shelves, before the doors open

Larkwell Foods: on-shelf availability, from raw data to the shop floor. Larkwell Foods is a fictitious UK food retailer, all data is
synthetic, and every estimate is labelled as one. Speaker notes follow each slide.

---

## 1. Fewer empty shelves, before the doors open
*Larkwell Foods · on-shelf availability, from raw data to the shop floor*

> **Notes (1 min).** Introduce yourself and the customer: a UK food retailer with 900 stores and about £8bn of food sales.
> Agenda: the outcome, a short demo of three moments in the day, how it's built, then value and the plan.
> Ask: "What does a good morning on availability look like for you today?"

---

## 2. Every morning, £1.09m of sales Larkwell can fix is at risk on 127,000 shelves

> **Notes (1 min).** About 206,000 shelves open empty or low each day. 127,000 of them have a cause someone can act on.
> Today the cause is found by hand, the next day, if at all. Pause, then: "Here's what changes."

---

## 3. What this delivers
- **£23.7m a year** of sales recovered in the base case (range £15.8m to £39.5m)
- **328,000 store hours a year** given back
- **98%** of empty shelves explained automatically, every morning
- From morning snapshot to **action at the shelf in minutes**
- Runs for roughly **£40k to £90k a year**

> **Notes (1.5 min).** Lead with the COO's numbers, then the Head of Availability's.
> These are estimates from the build's own data plus published shopper research; a 6-week pilot proves them.
> If asked "how sure are you?": "The base is measured; the prevention share is the pilot's job to prove, against control stores."

---

## 4. Why shelves are empty today

| Root cause | Gaps and lows | Sales at risk a day | Who can act |
|---|---|---|---|
| Sold more than forecast | 30,989 | £525k | Ordering team |
| Delivery arrived short | 40,711 | £232k | Depot and buying |
| Order blocked or cancelled | 24,491 | £143k | Depot |
| Phantom stock | 16,297 | £97k | Store |
| Written off as waste | 10,437 | £65k | Store and buying |
| Market-wide shortage | 16,573 | £90k | Substitute |
| Planned range exit | 62,251 | £372k | No action needed |
| Not yet known | 4,085 | £24k | Analyst |

> **Notes (1.5 min).** The evidence sits in six systems: stock, deliveries, orders, stock counts, waste and allocations. Nobody sees them together.
> 30% of gaps are planned exits that teams still chase. The biggest fixable cause is forecasting, not stores.

---

## 5. What changes, for each person
- **Store colleague:** scans the shelf; gets the cause and the next action in milliseconds; logs what they did in one tap
- **Head of Availability:** one governed view; 98% of gaps attributed; supplier and depot evidence; sees every action
- **COO:** fixable lost sales falling; store time given back; one number everyone trusts

> **Notes (1 min).** Bridge to the demo: "Let me show you those three moments."

---

## 6. Value for the COO

| Lever | Conservative | Base | Stretch |
|---|---|---|---|
| Sales recovered a year | £15.8m | £23.7m | £39.5m |
| Store time given back a year | £4.3m | £4.3m | £4.3m |
| Run cost a year (indicative) | up to £90k | up to £90k | up to £90k |
| Return on run cost | over 170x | over 260x | over 430x |

> **Notes (1 min).**
> - Controllable sales at risk: £1.09m a day, from the data.
> - Published research: 40% of shoppers facing an empty shelf buy elsewhere or not at all.
> - That gives £158m a year of controllable lost sales. The scenarios prevent 10%, 15% and 25% of it.
> - If challenged on cost: it's serverless, scales down overnight, and there's no big upfront build.
> - If asked "sales or profit?": sales. At a typical 25% gross margin the base case is about £5.9m of gross profit a year, still more than 60 times the run cost.

---

## 7. Value for the Head of Availability

| KPI | Today | With this build |
|---|---|---|
| Root cause confirmed | Manual, the next day | 98%, every morning |
| Time to action | The next day's report | Minutes |
| Supplier accountability | Anecdotal | Oldcastle Confectionery: 59% fill rate against a 99.0% contract |
| Depot accountability | Anecdotal | Merseyvale DC: 6,078 blocked lines across 130 stores |
| Planned exits chased | Often | Never: "no action needed" |

> **Notes (1 min).** This is the evidence for the supplier conversation and the depot fix, available on day one.

---

## 8. What I'll show you
1. Head office sees what's wrong, and why, by 6am
2. A colleague fixes it at the shelf
3. Anyone can ask, and the loop closes

Then: how it's built, and what it's worth.

> **Notes.** Switch to the app. Follow `docs/demo_script.md` (tell, show, tell).

---

## 9. One connected journey
Raw feeds → **Lakeflow** (bronze, silver, gold, root-cause rules) → **Unity Catalog** (metric view, tags, lineage) → **Lakebase** (Shelf Scan in milliseconds) →
**Databricks App** with **Gen AI** next best action and **Genie** → colleague actions → Lakebase → **Lakehouse Sync** → Unity Catalog.
The **daily job** runs and checks every stage.

> **Notes (1.5 min).**
> - **Executive altitude:** "One platform, end to end, checked every morning before anyone sees a number."
> - **Architect altitude:** walk the arrows. The same gold table serves analytics through the warehouse and lookups through Lakebase.

---

## 10. Under the hood
- **Data and governance:**
  - Auto Loader ingests 10 feeds incrementally
  - 38 data-quality expectations
  - Eight-step root-cause cascade, proven by an answer key: 205,834 of 205,834
  - Metric view, governed tags (pii), lineage, read-only app
- **Serving and AI:**
  - Lakebase lookups in milliseconds: over 100 times faster than the warehouse
  - Colleague actions back in Unity Catalog in under 30 seconds
  - The LLM words the playbook action; it never decides it
  - Daily MLflow evaluation with calibrated judges; Genie 12 of 12

> **Notes (1.5 min).** For the architect. Expect questions on data quality, security and integration: see the risks slide and the Q&A pack.

---

## 11. Proof it works

| Check | Result |
|---|---|
| Gaps and lows matching the answer key | 205,834 of 205,834 |
| Daily checks across the journey | 40 of 40, every stage, every morning |
| App end-to-end test | 65 of 65 |
| Shelf Scan lookup | 2.9 ms on Lakebase against 504 ms on the warehouse |
| A logged action back in Unity Catalog | 14 seconds |
| Genie benchmark | 12 of 12 |
| AI advice evaluation (48 cases) | 100% on all eight checks; judges calibrated on 19 hand-labelled answers |

> **Notes (1 min).** All of it is in the repository as text, regenerated from the live workspace.

---

## 12. Decisions and trade-offs

| Decision | Why | Trade-off |
|---|---|---|
| Rules cascade, not a model, for root cause | Explainable to a colleague, testable row by row | Machine learning saved for prediction, the next phase |
| Lakebase for Shelf Scan lookups | Over 100 times faster, built for thousands of users | A governed second copy |
| The app writes to Lakebase, not Delta | Transactional speed; read-only lakehouse access | Lakehouse Sync is in Beta |
| The LLM words the advice; it never decides it | No invented numbers or causes | Less "creative" advice, by design |
| Synthetic data with an answer key | Proves the pipeline on every run | Real-data noise to validate in the pilot |

> **Notes (1 min).** Pick the decision the architect cares about most and go one level deeper (see `docs/decisions.md`).

---

## 13. Risks and how we handle them

| Risk | How it's handled |
|---|---|
| Adoption in stores | Fits the handheld routine; actions take one tap; the pilot measures use |
| Feed data quality | 38 expectations; the daily checks fail loudly before anyone sees a number |
| Security and privacy | Unity Catalog grants; pii tagged; no personal data in Genie's views; a read-only app |
| Cost | Serverless, autoscaling Lakebase, model-cost controls |
| Wrong AI advice | Playbook-driven; a daily evaluation with thresholds; a template fallback |
| Beta feature (Lakehouse Sync) | A federated read over the Lakebase catalog as the fallback |

> **Notes (1 min).** Business risks first (adoption, cost), then technical (data quality, security, AI).

---

## 14. Value in 12 weeks

| Weeks | What | What it proves |
|---|---|---|
| 0-2 | Connect real stock, delivery and order feeds with Lakeflow; check the rules against 2 weeks of history | The rules match reality |
| 3-8 | Pilot in 20 stores, against 20 control stores | Controllable gap rate, time to action, colleague minutes |
| 9-12 | Roll out by division; supplier and depot scorecards | Value at scale |

**The ask:** approve the pilot, with your availability lead, two data engineers, and access to the feeds.

> **Notes (1 min).** Close on the outcome: "£23.7m a year of sales you can fix, proven in 6 weeks in 20 stores."

---

## Appendix A. Value model assumptions
| Input | Value | Source |
|---|---|---|
| Forecast demand | £22.6m a day (£8.2bn a year) | Build data |
| Controllable sales at risk | £1.09m a day | Build data |
| Share actually lost to the retailer | 40% | Gruen, Corsten and Bharadwaj (2002) |
| Prevented by faster, targeted action | 10%, 15% or 25% | Assumption, to test in the pilot |
| Manual checks per store per day | 20, at 3 minutes saved each, £13 an hour | Assumption |

## Appendix B. Run cost (indicative)
| Component | Estimate a year |
|---|---|
| Lakeflow pipeline and daily job | Low thousands of pounds |
| Lakebase (1-8 CU) | Under £10k |
| Databricks App | Under £10k |
| SQL warehouse | £10k-£20k |
| LLM next best action | £10k-£40k |
| **Total** | **About £40k-£90k** |

## Appendix C. Root-cause rules, in order
| # | Root cause | Evidence |
|---|---|---|
| 1 | Planned range exit | The line is exiting the store's range |
| 2 | Market-wide shortage | The allocation was cut for a market shortage |
| 3 | Delivery arrived short | Delivered less than ordered |
| 4 | Order blocked or cancelled | Latest order status is blocked or cancelled |
| 5 | Phantom stock | A stock count removed stock that wasn't there |
| 6 | Waste | Units written off |
| 7 | Sold more than forecast | Sales above forecast |
| 8 | Not yet known | No evidence: an analyst investigates |
