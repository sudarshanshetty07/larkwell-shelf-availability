# Demo script: tell, show, tell (about 17 minutes, plus questions)

The audience is the executive who funds the decision (a Chief Operating Officer) and the architect or data lead who has to live with it.
Larkwell Foods is fictitious and all data is synthetic.

**Before you start, open:**
- the app on the **Gaps/Lows Dashboard** (Support Centre, Store view);
- a second tab on **Shelf Scan** with Covent Garden selected;
- **AI Chat Assistant**;
- **Morning Briefing** with Covent Garden selected, scrolled to **Tomorrow morning**;
- **Data Journey**;
- the deck at the value slide.

## 0. Set up the demo (1 minute)

**Tell:**
> "Larkwell Foods runs 900 food stores and sells about £8bn a year. Every morning it opens with around 206,000 shelves empty or low.
> On the ones it can fix, about a million pounds of that day's sales is at risk. Today the cause is found by hand, the next day, if at all.
> I'll show you four moments. At 6am, head office sees what's wrong and why. A colleague fixes it at the shelf. You can see that it got done.
> And before close, the store sees which shelves will be empty tomorrow. Then I'll show you how it's built, and what it's worth."

## 1. Head office sees what's wrong, and why (3 minutes)

**Tell:** "First, where the problem is and what's causing it."

**Show:**
- **Dashboard:**
  - 133,765 gaps and 72,069 lows across 5.4 million product-locations.
  - The reason mix: planned range exits are separated out, so nobody chases them.
- **Drill down:** division, then area, then store, then product.
- Point at **Merseyvale DC**, with the most blocked orders: 6,078 lines across 130 stores.
- Point at **Oldcastle Confectionery**, on a 59% fill rate against a 99.0% contract.

**Tell:**
> "98% of gaps already have a confirmed cause, worked out from the raw signals overnight. The biggest controllable one is under-forecast,
> at about £0.5m a day. That's a forecasting conversation, not a store one. Your teams stop arguing about *what* and start fixing *why*."

## 2. A colleague fixes it at the shelf (4 minutes)

**Tell:** "Now the shop floor. A colleague sees an empty shelf and scans it."

**Show:**
1. On Shelf Scan, quick-scan the **supplier-short** line. Point out:
   - the status pill and the root cause in plain words;
   - the **"Answered from Lakebase in … ms"** line (a few milliseconds);
   - the next best action, for example "Raise a shortage query with the depot for the missing units".
2. Tap **Raised shortage query**. It appears in **Actions logged at Covent Garden** straight away.
3. Quick-scan the **planned range exit** line: "No action needed". That saves wasted effort on a gap that's deliberate.

**Tell:**
> "The colleague knows in a second what to do, and the advice can't contradict the playbook: we test that every day.
> And because the action is logged, head office knows it was done."

## 3. Anyone can ask, and the loop closes (3 minutes)

**Tell:** "Head office doesn't need a report built for every question."

**Show:**
- In AI Chat, ask: *"Which depot has the most order or delivery blocks?"* Genie answers with a table, and you can show the SQL.
- Ask: *"What actions have stores logged today, and for which root causes?"* The shortage query you just logged is there.
- Optional: one curated question, labelled as a curated analysis. It returns in about a second.

**Tell:**
> "Plain English, on one governed definition of every KPI. And what happened in the store a minute ago is already in the lakehouse."

## 4. Before close: tomorrow's empty shelves, flagged today (2 minutes)

**Tell:** "Everything so far explains this morning. This looks at tomorrow."

**Show:**
- **Morning Briefing**, Covent Garden, the **Tomorrow morning** section. A machine-learning model scored every ranged line for tomorrow morning.
- The first list is lines that **look fine now but are likely to be empty in the morning**, each with its reasons in plain English, for example "Today's delivery came 6 short" or "Empty or low on 3 of the last 7 days".
- The second list is **today's gaps and lows most likely to still be empty tomorrow**: fix those first.
- The line above the lists: how yesterday's list for this store did this morning.
- Optional: **Data Journey**, stage 6 (Predicted), or the curated chat question *"Which lines look fine now but are most likely to be empty tomorrow morning?"*

**Tell:**
> "Tested on a week it never saw, 60% of each store's top 25 were empty the next morning, against 46% for 'what's empty or low today'.
> On lines that look fine today, it's 12.4% against 2.2%. Only a version that beats both rules is used, and it's graded every morning."

## 5. How it's built (3 minutes; go deeper for the architect)

**Show:** the **Data Journey** tab, then the architecture slide.

**Tell (executive altitude):** "One platform, end to end. Every stage is checked every morning before anyone sees a number."

**Tell (architect altitude):**
- **Lakeflow:**
  - Auto Loader ingests 10 feeds.
  - Silver enforces its expectations (46 across the pipeline) and drops exactly the 120 malformed lines.
  - Gold applies the eight-step root-cause cascade.
  - An answer key proves all 205,834 exceptions are right.
- **Unity Catalog:**
  - the metric view;
  - governed tags with a PII tag on email;
  - automatic lineage;
  - the app's service principal is read-only.
- **Lakebase:**
  - a synced copy for millisecond lookups;
  - app writes go to Postgres;
  - Lakehouse Sync streams them back.
- **Machine learning:**
  - the pipeline builds 34 features per line per day, so training and scoring share one definition;
  - LightGBM, trained in MLflow on three weeks and tested on the next;
  - registered in Unity Catalog, and only a version that passes every gate gets the `champion` alias;
  - the daily job grades yesterday's predictions, then scores tomorrow.
- **AI:**
  - the LLM only words the playbook action;
  - an MLflow evaluation on 48 cases runs daily;
  - Genie is benchmarked 12/12.

## 6. Value, plan and the ask (2 minutes, on the slides)

**Tell:**
- **For you (COO):**
  - About £158m a year of controllable lost sales.
  - The base case recovers £23.7m, with a range of £15.8m to £39.5m.
  - About 328,000 store hours a year are given back.
  - Run cost is roughly £40k to £90k a year.
- **For the Head of Availability:**
  - 98% attributed automatically.
  - From snapshot to action in minutes.
  - Supplier and depot accountability, with evidence.
- **The ask:**
  - A 6-week pilot in 20 stores, measured against 20 control stores.
  - We need your availability lead, two data engineers, and access to the stock, delivery and order extracts.

## Switching altitude mid-answer

| If asked by | Lead with | Then |
|---|---|---|
| The COO: "What does it cost and when do I see value?" | "About £40k-£90k a year to run. You see it in a 6-week pilot, measured against control stores." | "The architecture is serverless and scales down at night, so there's no big upfront build." |
| The architect: "How do you know the root causes are right?" | "An answer key the pipeline never reads, matched row by row every morning: 205,834 of 205,834." | Back to the COO: "So the numbers your teams act on are tested before they see them." |
