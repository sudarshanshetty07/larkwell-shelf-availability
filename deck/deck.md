# Fewer empty shelves, before the doors open

The business deck as text: each slide's words, card by card, then its speaker notes. The deck itself is [larkwell_shelf_availability_deck.pdf](larkwell_shelf_availability_deck.pdf). Larkwell Foods is a fictitious UK food retailer, all data is synthetic, and every number on a slide is labelled measured, research, assumption or estimate.

---

## 1. Fewer empty shelves, before the doors open
*Larkwell Foods · on-shelf availability*

- Databricks Prepared for Larkwell Foods (fictitious) · Oct 2026

**Speaker notes**

> TIMING: 0:30 (0:00 to 0:30)
> KEY MESSAGE: Frame the customer and the session before anything else.
>
> SAY:
> Thanks for the time. I'm here from Databricks. Larkwell runs 900 food stores and sells about £8bn a year, and today is about one question its stores ask every morning: why is this shelf empty, and what do I do about it?
> In the next 25 minutes: the outcome, four moments in a Larkwell day in the live app, how it's built, and what it's worth. Please stop me with questions at any point.
>
> TRANSITION: Let me start with what you get.
>
> IF THE COO ASKS:
> - "Is this real data?" No. Larkwell is fictitious and the data is synthetic, built to the scale of a large UK grocer. The pilot is where we prove it on your data.
>
> IF THE ARCHITECT ASKS:
> - "What's actually live?" Everything you'll see runs on Databricks today: the pipeline, the governance, Lakebase, the AI and the app.

---

## 2. More sales, store time back, and every gap explained

- What Larkwell gets, with every number labelled by its source
- Assumption · £23.7m · a year of sales recovered in the base case (range £15.8m to £39.5m)
- Assumption · 328,000 · store hours a year given back: about £4.3m of capacity
- Measured · 98% · of gaps and lows get a confirmed cause automatically, every morning
- Measured · Minutes · from the morning snapshot to action at the shelf, instead of the next day
- About £40k to £90k a year to run · over 200× its cost in sales, and over 60× in gross profit · Estimate
- Measured · this build's data · Research · published research · Assumption · the pilot proves it · Estimate · indicative list prices

**Speaker notes**

> TIMING: 1:30 (0:30 to 2:00)
> KEY MESSAGE: Lead with the outcome in the COO's numbers, and be clear about what's measured and what's assumed.
>
> SAY:
> Here's the outcome. In the base case, £23.7m a year of sales recovered, with a range of £15.8m to £39.5m. About 328,000 store hours a year given back. 98% of gaps and lows explained automatically, every morning, and from the morning snapshot to action at the shelf in minutes. It runs for about £40k to £90k a year.
> Every number carries a label: measured in this build, published research, an assumption, or an estimate. The assumptions are exactly what the pilot is designed to prove.
>
> TRANSITION: So what's the problem we're solving?
>
> IF THE COO ASKS:
> - "How confident are you in £23.7m?" The base is measured: £1.09m a day of fixable sales at risk. The 40% loss rate is published research. What I'm assuming is how much faster action prevents, 10% to 25%. At 10% it's still £15.8m, and the pilot measures it against control stores.
> - "Is that sales or profit?" Sales. At a 25% gross margin it's about £5.9m of gross profit a year, still more than 60 times the run cost.
>
> IF THE ARCHITECT ASKS:
> - "Where does 98% come from?" The gold table: 201,749 of 205,834 gaps and lows have a confirmed cause. The other 4,085 go to an analyst rather than being guessed.

---

## 3. Every morning, £1.09m of fixable sales is at risk

- Larkwell Foods: 900 stores, 6,000 lines and about £8.2bn of sales a year
- Measured · 205,834 · shelves open empty or low, out of 5.4 million product-locations
- Measured · £1.09m · of that day's sales at risk on the shelves Larkwell can fix
- Measured + Research · £158m · a year of lost sales it could prevent: 40% of shoppers facing a gap buy elsewhere or not at all
- The evidence sits in six systems · Stock · Deliveries · Orders · Stock counts · Waste · Allocations · Nobody sees them together, so the cause is found by hand, the next day, if at all.
- Who feels it · COO lost sales, and store hours spent hunting for causes · Head of Availability no evidence for supplier and depot conversations · Store colleague an empty shelf, and no next step

**Speaker notes**

> TIMING: 1:30 (2:00 to 3:30)
> KEY MESSAGE: The cost is real and measured, and it persists because the evidence is split across six systems.
>
> SAY:
> Every morning Larkwell opens with about 206,000 shelves empty or low, out of 5.4 million. On the ones it can fix, £1.09m of that day's sales is at risk. Published research says 40% of shoppers who find a gap buy elsewhere or not at all, so that's about £158m a year of lost sales Larkwell could prevent.
> Why doesn't it? Because the evidence sits in six systems: stock, deliveries, orders, stock counts, waste and allocations. Nobody sees them together, so the cause is found by hand, the next day, if at all.
> Three people feel this: you as COO, the Head of Availability, and the colleague standing at the shelf.
>
> TRANSITION: So why are shelves empty?
>
> IF THE COO ASKS:
> - "Why £158m, and not £1.55m a day for a year?" I take out planned range exits and market-wide shortages, which nobody can fix, and count only the 40% of demand that's actually lost. Shoppers who substitute or come back aren't lost sales.
>
> IF THE ARCHITECT ASKS:
> - "Is 206,000 realistic?" It's 97.5% on-shelf availability. Published worldwide research puts out-of-stocks at about 8% on average, so this is a well-run grocer with a big absolute problem.

---

## 4. Most empty shelves are fixable; a third are deliberate

- Gaps and lows by root cause: the sales at risk each day, and who can act
- Root cause · Sales at risk a day · gaps and lows · Who can act
- £525k a day · is the biggest fixable cause: lines selling faster than forecast. A forecasting problem, not a store one.
- Sold more than forecast · £525k · 30,989 · Ordering team
- Planned range exit · £372k · 62,251 · No action needed
- Delivery arrived short · £232k · 40,711 · Depot and buying
- Order blocked or cancelled · £143k · 24,491 · Depot
- Phantom stock · £97k · 16,297 · Store
- 30% · of gaps and lows are planned range exits that teams still chase. They need no action at all.
- Market-wide shortage · £90k · 16,573 · Substitute
- Written off as waste · £65k · 10,437 · Store and buying
- Not yet known · £24k · 4,085 · Analyst
- Measured · Business date 19 October 2026 · 205,834 gaps and lows

**Speaker notes**

> TIMING: 1:30 (3:30 to 5:00)
> KEY MESSAGE: Most of it is fixable, the biggest fixable cause isn't the store, and a third is deliberate.
>
> SAY:
> When you work out the cause for every one of them, three things jump out.
> First, the biggest fixable cause is lines selling faster than forecast: £525k a day. That's a forecasting conversation, not a store one.
> Second, deliveries arriving short and blocked orders are another £375k a day between them, so depots and suppliers matter.
> Third, 30% of gaps and lows are planned range exits. They're deliberate, and teams still chase them. Stopping that is a saving from day one.
>
> TRANSITION: Let me show you what that looks like in a Larkwell morning.
>
> IF THE COO ASKS:
> - "Who owns each cause?" That's the right-hand column: ordering, depots and buying, stores, or an analyst. It's why each fix can go to the right team.
>
> IF THE ARCHITECT ASKS:
> - "How is the cause decided?" An eight-step rules cascade in the gold layer, in priority order: planned exit, market shortage, short delivery, blocked order, phantom stock, waste, then under-forecast. If nothing fits, it goes to an analyst. The rules are in the appendix.

---

## 5. Four moments in Larkwell's day

- What I'll show you in the app, and why each one matters
- 6:00 · head office · In the aisle · A minute later · Before close
- Head office sees what's wrong, and why · YOU'LL SEE · The dashboard and the drill-down, and the worst depot and supplier. · WHY IT MATTERS · 98% of gaps explained before the first store opens.
- A colleague fixes it at the shelf · YOU'LL SEE · Shelf Scan: the cause and the next action in milliseconds, and a one-tap action log. · WHY IT MATTERS · Action in seconds, at the shelf, not the next day.
- Anyone can ask, and the loop closes · YOU'LL SEE · Genie in plain English, and the action just logged, already governed. · WHY IT MATTERS · One number everyone trusts, and proof the work got done.
- The store sees tomorrow's gaps today · YOU'LL SEE · The gap-risk model's watch list, with its reasons, and how yesterday's list did. · WHY IT MATTERS · Act today on the shelves that will be empty tomorrow.
- Then: how it's built, and what it's worth.

**Speaker notes**

> TIMING: 1:00 (5:00 to 6:00)
> KEY MESSAGE: Tell them what they'll see, and why it matters, before the demo.
>
> SAY:
> I'll show you four moments. At 6am, head office sees what's wrong and why, before the first store opens. Then a colleague scans an empty shelf, gets the cause and the next action in milliseconds, and logs what they did with one tap. Then anyone can ask a question in plain English, and you'll see that the action the colleague just logged is already in the lakehouse, governed. And before close, the store sees which shelves are likely to be empty tomorrow morning, from a machine-learning model that's marked against reality every day. After that, how it's built.
>
> TRANSITION: Let me switch to the app. (Open the Gaps/Lows Dashboard, Support Centre view.)
>
> IF THE COO ASKS:
> - "Is this the real app?" Yes. It's deployed on Databricks and running on the synthetic estate: 5.4 million product-locations.

---

## 6. 6am: head office sees what's wrong, and why

- Moment 1 · the Gaps and Lows dashboard, with this build's figures
- Larkwell Shelf Availability · Gaps and Lows dashboard · Measured
- YOU'LL SEE · Every gap and low with its cause, by 6am A drill-down from division to the shelf The worst depot and supplier, with the evidence
- Gaps · 133,765
- Lows · 72,069
- On-shelf availability · 97.5%
- Cause confirmed · 98.0%
- Sales at risk by cause, a day · Sold above forecast · £525k · Delivery short · £232k · Order blocked · £143k · Phantom stock · £97k · Waste · £65k
- Flagged this morning · Drill down: division → area → store → line
- Merseyvale DC 6,078 blocked lines across 130 stores
- WHY IT MATTERS · Teams stop arguing about what's wrong and start fixing why. The biggest fixable cause is a forecasting conversation, not a store one.
- Oldcastle Confectionery 59.1% fill rate against a 99.0% contract

**Speaker notes**

> TIMING: 2:30 (6:00 to 8:30), including the demo
> KEY MESSAGE: Head office knows what's wrong and why before anyone arrives.
>
> SAY:
> TELL: First, head office at 6am.
> SHOW (in the app): the dashboard, 133,765 gaps and 72,069 lows, with the cause mix and planned exits separated out. Drill down: division, area, store, product. Point at Merseyvale DC: 6,078 blocked lines across 130 stores. Point at Oldcastle Confectionery: a 59% fill rate against a 99% contract.
> TELL: 98% of gaps already have a confirmed cause, worked out from the raw signals overnight. Your teams stop arguing about what's wrong and start fixing why, and the biggest fixable cause is a forecasting conversation.
> FALLBACK: if the app is slow, this slide is the same view with the same numbers.
>
> TRANSITION: Now the shop floor.
>
> IF THE COO ASKS:
> - "Can I hold the depot to account with this?" Yes. Every blocked line comes with the store, the order and the date. That's the evidence for the depot conversation, from day one.
>
> IF THE ARCHITECT ASKS:
> - "What's behind the dashboard?" The SQL warehouse over the gold table and the metric view: one definition of every KPI, so the dashboard and Genie can't disagree.

---

## 7. At the shelf: the cause and the fix in milliseconds

- Moment 2 · Shelf Scan at Covent Garden, with the app's real answer
- Scan
- Shelf Scan · Covent Garden · Guacamole 150g 2 for £5 · GAP · Nothing on the shelf · 18 units short on the last delivery Supplier: Heatherleigh Deli Foods Depot: Riverside DC · Raised shortage query · Counted stock · Answered from Lakebase in 2.5 ms
- The playbook decides. The model words it. · # The rules pick the cause. # The playbook picks the action: ACTION_BY_REASON = { "SUPPLIER_SHORT": "Raise a shortage query...", "KNOWN_GAP": "No action needed...", # ...eight causes in all } # The LLM only words it. · Every number must appear in the facts it's given It can't contradict the playbook: tested every day A fixed template answers if the model is down
- A colleague scans the shelf-edge label of an empty space.
- Look up · 2.5 ms · Lakebase
- Root cause The last delivery arrived short
- One primary-key lookup in Lakebase, synced from the gold table.
- Advise · async · LLM
- The playbook picks the action; the LLM words it for the colleague.
- Next best action The last delivery arrived 18 units short, which is why there's a gap on the shelf. Raise a shortage query with Riverside DC for the missing units and check when the next delivery is due.
- Act · 14 s · Unity Catalog
- One tap logs it, and Lakehouse Sync brings it back to Unity Catalog.

**Speaker notes**

> TIMING: 3:30 (8:30 to 12:00), including the demo
> KEY MESSAGE: The colleague gets the cause and the right action in seconds, and the AI can't make things up.
>
> SAY:
> TELL: Now a colleague at Covent Garden finds an empty shelf: Guacamole, two for £5.
> SHOW (in the app, Shelf Scan): scan it. The answer comes back from Lakebase in about 3 milliseconds: a gap, because the last delivery arrived 18 units short. The next best action: raise a shortage query with Riverside DC. Tap 'Raised shortage query'; it appears in the store's action list straight away. Then scan a planned range exit: 'No action needed', which saves a wasted chase.
> TELL: The colleague knows in a second what to do, and the advice can't contradict the playbook. The rules choose the cause, the playbook chooses the action, and the model only words it. We test that every day.
> FALLBACK: this slide shows the same screen and the app's real answer.
>
> TRANSITION: Now anyone can ask, and you'll see that action again.
>
> IF THE COO ASKS:
> - "What if the AI says something wrong?" It can only word what the rules and the playbook decide; every number must come from the facts it's given; and if the model is down, a fixed template answers. 48 real cases are tested every morning, and if quality drops, the job fails.
>
> IF THE ARCHITECT ASKS:
> - "Why Lakebase and not the warehouse?" A scan is a point lookup from thousands of handhelds: 2.5 ms on Lakebase against 634 ms on the warehouse. Dashboards stay on the warehouse. One gold table, two serving paths.
> - "Which model?" Claude Sonnet 4.5 on Databricks Model Serving. The judges that test it run on GPT-5.5, a different model family.

---

## 8. Anyone can ask, and the loop closes

- Moment 3 · Genie on the metric view, and the action just logged
- Ask the data · Genie · Which depot has the most order or delivery blocks? · Show SQL · Built on the metric view · What actions have stores logged today? · 16 actions so far; 7 are shortage queries on lines that arrived short.

| Depot | Blocked lines | Stores |
|---|---|---|
| Merseyvale DC | 6,078 | 130 |
| Wealden DC | 4,419 | 140 |
| Riverside DC | 3,848 | 175 |

- The loop closes, within seconds
- A colleague taps “Raised shortage query” Covent Garden · Guacamole 150g 2 for £5
- Merseyvale DC has the most: 6,078 blocked lines across 130 stores.
- Written to Lakebase in milliseconds Postgres: the app never writes to the lakehouse
- Lakehouse Sync streams the change Every insert and update, with its history
- In Unity Catalog 14 seconds later gold.colleague_actions: governed, with no personal data

**Speaker notes**

> TIMING: 2:30 (12:00 to 14:30), including the demo
> KEY MESSAGE: One governed definition of every number, and proof the work got done, within seconds.
>
> SAY:
> TELL: Head office doesn't need a report built for every question.
> SHOW (in the app, AI Chat): ask 'Which depot has the most order or delivery blocks?' Genie answers from the governed metric view: Merseyvale DC, 6,078 lines across 130 stores, and you can show the SQL. Then ask 'What actions have stores logged today, and for which root causes?' The shortage query you just logged is there.
> TELL: Plain English, on one governed definition of every KPI. And what happened in a store a minute ago is already in the lakehouse: the app writes to Lakebase, and Lakehouse Sync brings it back to Unity Catalog in about 14 seconds.
>
> TRANSITION: Last moment: before close, tomorrow. (Open Morning Briefing, Covent Garden.)
>
> IF THE COO ASKS:
> - "Can I trust Genie's numbers?" It's benchmarked on 12 questions with known answers and scores 12 of 12. And it uses the same metric view as the dashboard, so the numbers can't disagree.
>
> IF THE ARCHITECT ASKS:
> - "Where does personal data go?" Emails stay in one restricted table, tagged pii. The views Genie sees carry no personal data.

---

## 9. Before close: tomorrow's empty shelves, flagged today

- Moment 4 · Covent Garden's briefing, from the gap-risk model
- Larkwell Shelf Availability · Morning briefing · Covent Garden · Measured · Tomorrow morning · ML · ml.gap_risk v2 · Predicted the day before, for 20 Oct. Tested on a week it never saw: 60% of each store's top 25 were empty the next morning, against 46% for “what's empty or low today”. Here, yesterday's list: 14 of 25 empty this morning. · Look fine now, likely to be empty tomorrow: worth a check before close · Fix first: Easy Peeler Clementines 600g Multi-Buy (gap now, 77% likely still empty tomorrow) and 4 more of today's gaps and lows.

| Product | Chance | Why |
|---|---|---|
| Orange Squash 1L | 12% | Empty on 6 of the last 7 days |
| Organic Feta 200g | 12% | Empty yesterday, refilled today |
| Coronation Chicken Sandwich 2pk Family Pack | 11% | Empty on 2 of the last 7 days |
| Whole Milk 4 pints Family Pack | 10% | Empty on 3 of the last 7 days |
| Organic Wholemeal Loaf 400g | 9% | Shelf only 33% full; Empty yesterday, refilled today |

- HOW IT WORKS · Lakeflow builds 34 features per line, every day · LightGBM trained in MLflow, tested on a later week · Champion in Unity Catalog only if it beats both rules · Scored every day for tomorrow; graded every morning
- WHY IT MATTERS · Stores act today on the shelves that will be empty tomorrow. And the model is marked every day against what really happened.

**Speaker notes**

> TIMING: 2:30 (14:30 to 17:00), including the demo
> KEY MESSAGE: The store acts today on the shelves that will be empty tomorrow, and the model is marked every day.
>
> SAY:
> TELL: Everything so far explains this morning. The last moment looks at tomorrow.
> SHOW (in the app, Morning Briefing, Covent Garden): scroll to 'Tomorrow morning'. A machine-learning model scored every ranged line for tomorrow morning. The first list is lines that look fine now but are likely to be empty in the morning, each with its reasons in plain English, for example 'Empty on 6 of the last 7 days'. The second is today's gaps and lows most likely to still be empty tomorrow: fix those first. Point at the line above the lists: yesterday's list for this store had 14 of 25 lines empty this morning. If there's time, open Data Journey: stage 6, Predicted.
> TELL: Tested on a week it never saw, 60% of each store's top 25 were empty the next morning, against 46% for 'what's empty or low today'. On lines that look fine today, it's 12.4% against 2.2% for 'lowest stock first'. It's trained on the same governed data, registered in Unity Catalog, and only a version that beats both rules is ever used. And it's graded every morning against what really happened.
> FALLBACK: this slide shows the same lists, with the app's real predictions.
>
> TRANSITION: So what changes on Monday morning? (Switch back to the deck.)
>
> IF THE COO ASKS:
> - "How many gaps does it prevent?" I don't claim a number yet. The model's job is to rank tomorrow's risk, and it's measured on that every morning. How many gaps acting on the list prevents is what the pilot measures, against control stores. It's upside on top of the £23.7m.
> - "Isn't a 1-in-8 hit rate low?" Not for shelves that look fine: picked at random, about 1 in 130 would be empty. 'Lowest stock first' gets 2.2%. The model gets 12.4%, so a check before close finds real problems, not noise.
>
> IF THE ARCHITECT ASKS:
> - "Why LightGBM?" It's a yes-or-no about tomorrow for 5.4 million rows of tabular features every day. Gradient-boosted trees are the standard tool: they train in minutes, score in seconds, and give per-feature contributions, which we turn into the plain-English reasons.
> - "How do you stop it seeing the future?" The pipeline builds the features from today and the six days before. The label, tomorrow's shelf, is joined on only at training time. And it's tested on a later week than it was trained on.
> - "What stops a bad retrain going live?" Gates. It has to beat both rules and the current champion on the same test week, and be calibrated. Only then does it get the champion alias in Unity Catalog, which is what the daily job scores with.

---

## 10. What changes on Monday morning

- The same morning, for the three people who feel it
- Store colleague · At the shelf · TODAY · An empty shelf, no reason, and no next step. · WITH THIS BUILD · Scans it: the cause and next action in seconds; before close, the shelves likely to be empty tomorrow. · KPI Colleague minutes per check
- Head of Availability · Domain owner · TODAY · Causes found by hand, the next day. Supplier and depot calls without evidence. · WITH THIS BUILD · 98% explained by 6am, with evidence for every supplier and depot, and every action visible. · KPI Controllable gap rate · time to action
- COO · Executive sponsor · TODAY · £158m a year of preventable lost sales, and store hours spent hunting for causes. · WITH THIS BUILD · Fixable lost sales falling, store time back, and one number everyone trusts. · KPI Sales recovered against control stores

**Speaker notes**

> TIMING: 1:00 (17:00 to 18:00)
> KEY MESSAGE: Land the demo in business terms, for each person in the room.
>
> SAY:
> So, what changes on Monday morning. The colleague goes from an empty shelf with no reason to the cause and the next action in seconds, and before close, the shelves likely to be empty tomorrow. The Head of Availability goes from causes found by hand the next day to 98% explained by 6am, with evidence for every supplier and depot conversation. And for you as COO: fixable lost sales falling, store time back, and one number everyone trusts. Each has a KPI the pilot measures.
>
> TRANSITION: Let me show you, briefly, how it's built.
>
> IF THE COO ASKS:
> - "What does the colleague have to do differently?" Nothing new: they scan the shelf as they do today, and logging an action is one tap.

---

## 11. One platform, end to end, checked every morning

- Raw feeds to the shop floor and back, in one governed bundle
- Raw feeds stock, deliveries, orders, counts, waste, allocations
- Lakeflow Auto Loader, 46 checks, root cause, ML features
- Unity Catalog metric view, tags, lineage, grants
- Lakebase synced gold table: lookups in milliseconds
- Databricks App Shelf Scan, dashboards, Genie chat, Data Journey
- Gap-risk model LightGBM in MLflow; champion in Unity Catalog
- Genie plain-English questions over the metric view
- Lakehouse Sync actions back to Unity Catalog within seconds
- Lakebase ops actions, scans, AI advice, feedback
- Gen AI next best action Model Serving, with MLflow evaluation daily
- A Lakeflow Job runs the day: land → pipeline → Lakebase → 43 checks → predict gap risk, evaluate AI · one Declarative Automation Bundle deploys it all

**Speaker notes**

> TIMING: 2:00 (18:00 to 20:00)
> KEY MESSAGE: One platform, end to end, checked every morning before anyone sees a number.
>
> SAY:
> FOR THE COO: one platform, end to end, checked every morning before anyone sees a number.
> FOR THE ARCHITECT, walk the arrows: ten raw feeds land in a governed volume. Lakeflow ingests them incrementally with Auto Loader, enforces 46 data-quality checks and works out the cause. It also builds the gap-risk model's features: the model is trained in MLflow and registered in Unity Catalog, which governs it all, with a metric view for every KPI. Gold is synced into Lakebase for the scans; the app writes actions to Lakebase, and Lakehouse Sync brings them back to Unity Catalog, where Genie and the dashboards see them. The LLM's advice is evaluated every day. A Lakeflow Job runs the whole day: it checks every stage, grades yesterday's predictions, makes today's, and one bundle deploys it all.
>
> TRANSITION: And all of it is tested.
>
> IF THE COO ASKS:
> - "Do we need new systems?" No. It reads your existing extracts and runs on one platform, and it doesn't change your ordering systems.
>
> IF THE ARCHITECT ASKS:
> - "How does it scale?" Everything is serverless. Rebuilding all 36 days from scratch, 194 million product-location days, took under 9 minutes; a normal day reads only its own files. Lakebase autoscales from 1 to 8 compute units. At ten times the scale I'd make gold and the features incremental.
> - "How does it connect to our systems?" It starts from files in a governed volume, so anything that can drop an extract works today. Lakeflow Connect covers databases and SaaS sources.

---

## 12. Every number is tested before anyone sees it

- Execution evidence from the live workspace, kept as text in the repo
- Measured · 205,834 · of 205,834 gaps and lows match an answer key the pipeline never reads, row by row
- Measured · 43 of 43 · daily checks on every stage, from raw files to the model's inputs
- Measured · 72 of 72 · end-to-end tests on the deployed app
- Measured · 2.5 vs 634 ms · a Shelf Scan lookup on Lakebase, against the SQL warehouse
- Measured · 12 of 12 · Genie benchmark questions answered correctly
- Measured · 100% · of AI advice passes all eight checks; the judges agree with 19 hand-labelled answers
- Measured · 60% vs 46% · of each store's top-25 watch list empty next morning, against the today rule, on an unseen week
- Measured · 12.4% vs 2.2% · of lines that looked fine but were on the list were empty next morning, against lowest stock first
- Every failed run is kept in the evidence, with what it caught. No threshold was lowered to get a pass.

**Speaker notes**

> TIMING: 1:00 (20:00 to 21:00)
> KEY MESSAGE: The numbers your teams act on are tested before they see them.
>
> SAY:
> Everything you've seen is tested. The data comes with an answer key the pipeline never reads, and all 205,834 gaps and lows match it row by row. 43 checks run every morning, across every stage. The app passes 72 of 72 end-to-end tests. Genie scores 12 of 12, and the AI advice passes all eight checks, with judges calibrated against hand-labelled answers. The gap-risk model beat both rules on a week it never saw, and it's graded every morning. The evidence is all in the repository, as text. When a check failed, we fixed the cause; we never lowered a threshold.
>
> TRANSITION: So what's it worth?
>
> IF THE ARCHITECT ASKS:
> - "What did the checks catch?" Real bugs: source IDs that restart every day, a generator that wasn't reproducible across machines, and a job repair that checked the wrong day. Each was fixed, and each is kept in the evidence.

---

## 13. £23.7m a year back, for under £90k a year to run

- For the COO: the base case, and what's measured or assumed
- Measured · £1.09m · a day of controllable sales at risk
- × · × 364 = · × · =
- Research · 40% · of at-risk demand is lost to the retailer
- Measured + Research · £158m · a year of lost sales Larkwell could prevent
- Assumption · 15% · prevented by faster, targeted action (10% to 25%)
- Assumption · £23.7m · a year recovered in the base case (£15.8m to £39.5m)
- Assumption · £5.9m · a year of gross profit in the base case, at a 25% margin
- Assumption · £4.3m · of store time a year: 328,000 hours, counted as capacity, not headcount
- Estimate · Over 200× · the run cost in sales, and over 60× in gross profit; about £40k to £90k a year to run
- Research: Gruen, Corsten and Bharadwaj, Retail Out-of-Stocks (GMA, FMI and CIES, 2002): 31% of shoppers buy elsewhere and 9% don't buy. The assumptions are what the pilot tests.

**Speaker notes**

> TIMING: 1:30 (21:00 to 22:30)
> KEY MESSAGE: £23.7m a year back for under £90k to run, and you can see exactly which parts are measured and which the pilot proves.
>
> SAY:
> Here's how the £23.7m is built. £1.09m a day of fixable sales at risk: measured. 40% of that demand is lost to the retailer: published research. That's about £158m a year of lost sales you could prevent. If faster, targeted action prevents 15% of it, that's £23.7m a year; at 10% it's £15.8m, at 25% it's £39.5m. That 15% is the assumption the pilot tests.
> In gross profit, that's about £5.9m a year. On top, about 328,000 store hours, as capacity, not headcount. All for roughly £40k to £90k a year to run.
>
> TRANSITION: And for the Head of Availability.
>
> IF THE COO ASKS:
> - "Why should I believe 15%?" You shouldn't have to: we measure it. The pilot runs 20 stores against 20 matched control stores for 6 weeks.
> - "Can I cut 328,000 hours?" No. It's time given back for replenishment and customers, not a headcount saving.

---

## 14. Every gap explained, every supplier accountable

- For the Head of Availability: the KPIs that change from day one
- KPI · Today · With this build
- Root cause confirmed · By hand, the next day · → · 98%, automatically, every morning · Measured
- Time to action · The next day's report · → · Minutes, at the shelf · Measured
- Supplier accountability · Anecdotal · → · Oldcastle Confectionery: 59.1% fill against a 99.0% contract · Measured
- Depot accountability · Anecdotal · → · Merseyvale DC: 6,078 blocked lines across 130 stores · Measured
- Planned exits chased · Often · → · Never: 30% of gaps are marked “no action needed” · Measured

**Speaker notes**

> TIMING: 1:00 (22:30 to 23:30)
> KEY MESSAGE: The domain owner gets evidence and accountability from day one.
>
> SAY:
> For the Head of Availability: root causes confirmed for 98% of gaps every morning instead of by hand the next day; time to action in minutes; and evidence for the supplier and depot conversations from day one: Oldcastle Confectionery at a 59% fill rate against a 99% contract, and Merseyvale DC with 6,078 blocked lines. And planned exits are never chased again.
>
> TRANSITION: Where does this go next?
>
> IF THE COO ASKS:
> - "How quickly do we see this?" The supplier and depot evidence is there in the first week of the pilot, because it comes straight from your existing feeds.

---

## 15. From diagnose, to predict, to act

- Diagnose and a first predict are built, on the same data; act comes next
- Horizon 1 · Built · this prototype · Diagnose · A confirmed cause on every gap and low by 6am Scan-to-why at the shelf, in milliseconds Every action logged and governed · KPI: time to diagnose, next day → minutes
- Horizon 2 · Built · first version · Predict · Every line scored every day for the next morning MLflow, a Unity Catalog champion, graded every day Next: real history, intraday feeds, store task lists · KPI: share of gaps prevented
- Horizon 3 · Then · Act · Agents draft supplier claims and order uplifts A person approves anything with money attached Colleague feedback sharpens the rules · KPI: share of fixes automated
- Rules explain; ML predicts · The LLM words, never decides · Every AI change is evaluated · One governed data product

**Speaker notes**

> TIMING: 0:45 (23:30 to 24:15)
> KEY MESSAGE: Diagnose is built, a first version of predict is built and graded daily, and act comes next.
>
> SAY:
> Horizon one, diagnose, is what you saw first. Horizon two, predict, is built in a first version: the gap-risk model, trained in MLflow, registered in Unity Catalog, and graded every morning. What it needs next is your real history, intraday stock feeds, and store task lists built from it. Then act: agents that draft supplier claims and order uplifts, with a person approving anything with money attached.
>
> TRANSITION: Here's how we'd prove it.
>
> IF THE COO ASKS:
> - "When do we get prediction?" It's here in a first version: every line scored every day for tomorrow. The pilot retrains it on your real history and measures the gaps it prevents, against control stores.
>
> IF THE ARCHITECT ASKS:
> - "Why rules for the cause and ML for the forecast?" The cause has to be explainable to a colleague and testable row by row, so it's rules. Tomorrow's risk is a ranking problem where a model beats any rule, so that's ML, and it's held to beating the rules before it's used.
> - "Is the model production-ready?" The method is: governed features, a test on a later week, gates, a champion alias and a daily grade. What it needs is real history, ideally a year with promotions and seasonality, which the pilot brings.

---

## 16. Proven in 12 weeks, against control stores

- A pilot measured on these KPIs, with exit criteria agreed up front
- WEEKS 0 TO 2 · Connect · Connect real stock, delivery and order feeds with Lakeflow; check the rules against two weeks of history. · PROVES · The rules match reality
- WEEKS 3 TO 8 · Pilot · 20 stores against 20 matched control stores, with the app in colleagues' hands. · PROVES · Gap rate, time to action, colleague minutes
- WEEKS 9 TO 12 · Scale · Roll out by division, with supplier and depot scorecards. · PROVES · Value at scale
- What we need from you your availability lead · two data engineers · access to the stock, delivery and order extracts
- The ask: approve the 6-week pilot in 20 stores, measured against 20 control stores.

**Speaker notes**

> TIMING: 1:00 (24:15 to 25:15)
> KEY MESSAGE: A low-risk, measured path to value in 12 weeks.
>
> SAY:
> Weeks 0 to 2: connect your real stock, delivery and order feeds with Lakeflow, and check the rules against two weeks of history with your availability team. Weeks 3 to 8: pilot in 20 stores against 20 control stores. Weeks 9 to 12: roll out by division, with supplier and depot scorecards. We need your availability lead, two data engineers and access to the extracts. The ask: approve the pilot.
>
> TRANSITION: To close.
>
> IF THE COO ASKS:
> - "What does success look like?" A lower controllable gap rate in pilot stores than in control stores, time to action in minutes, and colleagues using it. We agree the bar before week 3.
>
> IF THE ARCHITECT ASKS:
> - "What do you need from my team?" Two data engineers, part-time, and access to the stock, delivery and order extracts. Everything else is already built.

---

## 17. Three things to take away

- Fewer empty shelves, before the doors open
- Diagnosis, not detection, is the bottleneck · A confirmed cause on 98% of gaps by 6am, and the next action at the shelf in milliseconds.
- Rules explain, ML predicts, AI words it · Causes from governed SQL; tomorrow's risk from a model graded every morning; the LLM only words the playbook.
- One platform, end to end · Lakeflow, Unity Catalog, Lakebase, ML, Gen AI, Genie and an App: one bundle, checked every morning.
- The ask: approve the 20-store pilot, measured against 20 control stores.
- Thank you. I'd love your questions.

**Speaker notes**

> TIMING: 0:30 (25:15 to 25:45)
> KEY MESSAGE: Close on the three ideas and the ask, then invite questions.
>
> SAY:
> Three things to take away. Diagnosis, not detection, is the bottleneck, and this puts a cause on 98% of gaps by 6am. Rules explain today, a model predicts tomorrow, the AI only words the advice, and every one of them is tested. And it's one platform, end to end. The ask: approve the 20-store pilot. Thank you; I'd love your questions.

---

## 18. Appendix
*Answers to likely questions, for either of you*


**Speaker notes**

> Appendix: open these only when a question calls for them. Each one answers a likely objection.

---

## 19. Under the hood, for the architect

- What each Databricks product does in this build, with the detail behind it
- Lakeflow · Auto Loader: 10 feeds; a full refresh rebuilt all 36 days at once 27 SQL files: bronze, silver, gold and the ML features 46 expectations; exactly the 120 malformed lines dropped
- Unity Catalog · One catalog: medallion schemas and governed volumes A metric view: one definition of every KPI, for the app and Genie Governed tags (pii on email), lineage, a read-only app identity
- Lakebase · Gold synced to Postgres: 5.4M rows, keyed on store and line 2.5 ms lookups, against 634 ms on the warehouse The app writes to Postgres; Lakehouse Sync streams changes back
- Machine learning · LightGBM on 34 features the pipeline builds MLflow run; Unity Catalog model with a gated champion alias Scored every day, graded every morning
- Gen AI · Claude Sonnet 4.5 on Model Serving words the playbook action Daily MLflow evaluation: 48 cases, six code checks, two judges Judges on GPT-5.5, calibrated on 19 hand-labelled answers
- Genie · Over the metric view, gold, supplier performance and the actions views Text instructions and 9 example queries Benchmark: 11, 11, then 12 of 12
- App and operations · FastAPI and a single-page app on Databricks Apps One bundle: pipeline, three jobs and the app Daily job: land, pipeline, Lakebase, 43 checks, ML, AI evaluation
- Testing · An answer key matched row by row, every morning 43 daily checks; 72 of 72 end-to-end tests on the app Every failed run kept in the evidence

**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: The detail behind each product, for the technical stakeholder.
>
> SAY:
> Use this when the architect wants detail. Answer the question first, then bridge back to the COO: 'which is why the numbers your teams act on are tested before they see them.'

---

## 20. Decisions and trade-offs

- Each choice, why it was made, and what it costs

| Decision | Why | Trade-off |
|---|---|---|
| Rules for today's cause; ML for tomorrow's risk | Rules: explainable, tested row by row. ML: ranks risk better than any rule | The model needs real history: the pilot retrains it |
| Features in the pipeline; labels joined at training | One definition for training and scoring; nothing from the future leaks in | Six weeks recomputed daily, for now |
| Lakebase for Shelf Scan, the warehouse for analytics | Point lookups for thousands of colleagues, over 100× faster | A second, governed, read-only copy |
| App writes go to Lakebase, not Delta | Transactional speed; the app can't write to the lakehouse | Lakehouse Sync is in Beta; the fallback is a federated read |
| The LLM words the advice; it never decides it | No invented numbers or causes | Less 'creative' advice, by design |
| Daily snapshot sync, not continuous | Stock arrives once a day, so continuous sync would cost more for nothing | Revisit when stock feeds go intraday |
| Synthetic data with an answer key | Proves the pipeline on every run | Real-data noise is validated in the pilot |


**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Every decision has a reason and a known cost.
>
> SAY:
> Pick the decision the architect cares about and go one level deeper; the full reasoning is in docs/decisions.md in the repository.

---

## 21. Risks, and how each is handled

- Business risks first, then technical

| Risk | How it's handled |
|---|---|
| Adoption in stores | It fits the handheld routine; one tap to log; the pilot measures use as a KPI |
| The value doesn't materialise | Measured against 20 control stores, with exit criteria agreed before week 3 |
| Cost | Serverless and autoscaling, about £40k to £90k a year; a smaller model or caching cuts the LLM cost |
| Feed data quality | 46 expectations and 43 daily checks fail loudly before anyone sees a number |
| Wrong AI advice | Playbook-driven; a daily evaluation with thresholds that fail the job; a template fallback |
| Security and privacy | Least-privilege grants; pii tagged; no personal data in Genie's views; a read-only app identity |
| Beta feature (Lakehouse Sync) | A federated read over the Lakebase catalog, behind the same views |
| Model learned on simulated history | It proves the method; the pilot retrains it on real history before anyone relies on it |
| A retrain makes it worse | Gates: it must beat both rules and the champion; it's graded every morning |


**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Each risk has an owner and a mitigation.
>
> SAY:
> Lead with the business risks for the COO (adoption, value, cost), then the technical ones for the architect.

---

## 22. How the AI advice is tested, every day

- The app's exact prompt, tested on 48 real cases; a miss fails the job

| Check | Type | What it checks | Bar | Final run |
|---|---|---|---|---|
| Numbers grounded | Code | Every number appears in the facts given | 98% | 100% |
| Follows the playbook | Code | The advice contains the playbook action | 95% | 100% |
| No contradiction | Code | No forbidden advice, such as chasing a supplier for a planned exit | 100% | 100% |
| No internal codes | Code | No codes such as SUPPLIER_SHORT | 100% | 100% |
| Units only | Code | No invented units such as cases | 100% | 100% |
| Concise | Code | At most three sentences and 75 words | 90% | 100% |
| Plain English | LLM judge | Plain, friendly British English for a colleague | 90% | 100% |
| Consistent with the playbook | LLM judge | Doesn't contradict the recommended action | 95% | 100% |
| Judge calibration | Both judges | Agree with 19 hand-labelled good and bad answers | 100% | 100% |

- The judges run on GPT-5.5, a different model family from the advice model (Claude Sonnet 4.5). No threshold was lowered to get a pass.

**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: The AI is held to measurable bars, and the judges are themselves tested.
>
> SAY:
> Code checks cover anything exactly checkable; LLM judges cover tone and consistency, run on a different model family, and must agree with hand-labelled answers before they're trusted.

---

## 23. The gap-risk model, tested like everything else

- Trained on three weeks, tested on the next, graded every morning

| Test week, all 900 stores | Model | Today rule | Lowest cover |
|---|---|---|---|
| Ranks tomorrow's empty shelves first (AUC) | 0.93 | 0.83 | 0.83 |
| Top 25 per store: empty next morning | 60% | 46% | 46% |
| Top 25: share of tomorrow's empties caught | 16% | 12% | 12% |
| Looks fine today: AUC | 0.86 | 0.66 | 0.66 |
| Looks fine, top 25: empty next morning | 12.4% | 2.2% | 2.2% |

- Predicts an unplanned empty shelf tomorrow morning, for every ranged line, the day before · Learns from 34 pipeline features; most weight on today's shelf, the last 7 days and how full it is · Trained 21 Sep to 11 Oct; LightGBM, 169 trees; logged to MLflow · Gated beats both rules and the champion, is calibrated, and passes the data checks · Graded every morning: top-25 lists 58% to 61% empty over the last 7 mornings
- Measured · Test week 12 Oct to 18 Oct, never seen in training. Both rules use only what a store sees in its morning report.
- Learned on simulated history: this proves the method. The pilot retrains it on real history and measures the gaps it prevents.

**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: The model is held to the same standard as everything else: it has to beat the rules.
>
> SAY:
> Use this when either of you asks how good the model is. Lead with the watch list: of each store's top 25, 60% were empty the next morning, against 46% for the today rule. Then the harder case: lines that look fine, 12.4% against 2.2%. Be clear it learned on simulated history: this proves the method, and the pilot retrains it on real data.

---

## 24. Security and governance

- Least privilege by default; no personal data where Genie can see it
- Read-only app identity · The app's service principal reads gold and ops only. It can't write to the lakehouse.
- Lakebase roles · It reads the serving table, and reads, inserts and updates its own tables. No deletes.
- Personal data · Emails sit in one restricted table, tagged pii. Every view built for Genie leaves them out.
- Tags and lineage · Governed data_classification and domain tags; lineage captured automatically.
- In production · On-behalf-of-user auth, so Unity Catalog row filters apply per colleague.
- This build · A fictitious retailer and synthetic data; a scan blocks publishing on names, hosts, emails or tokens.

**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Least privilege and no personal data in the analytical layer.
>
> SAY:
> Answer the COO at their altitude first ('your data stays in your governed platform, and the app can only read what it needs'), then give the architect the detail on this slide.

---

## 25. Value model: inputs and sources

- Every input labelled: measured, published research, or an assumption

| Input | Value | Source |
|---|---|---|
| Forecast demand | £22.6m a day (about £8.2bn a year) | Measured |
| Controllable sales at risk | £1.09m a day, across 127,010 gaps and lows | Measured |
| Share of at-risk demand lost to the retailer | 40% (31% buy elsewhere, 9% don't buy) | Research: Gruen, Corsten and Bharadwaj (2002) |
| Prevented by faster, targeted action | 10%, 15% or 25% | Assumption: the pilot measures it |
| Gross margin | 25% | Assumption |
| Manual checks per store per day | 20, saving 3 minutes each, at £13 an hour | Assumption |


**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Every input has a source, and the assumptions are the pilot's job to prove.
>
> SAY:
> Walk the COO through which inputs are measured and which are assumed; offer to run the pilot against their own assumptions.

---

## 26. Run cost (indicative)

- List prices; to confirm with the account team

| Component | Assumption | Estimate a year |
|---|---|---|
| Lakeflow pipeline, daily job and the gap-risk model | Serverless, about 20 minutes a day, and a weekly retrain | Low thousands of pounds |
| Lakebase | Autoscaling 1 to 8 CU, about 2 CU on average | Under £10k |
| Databricks App | One medium app, always on | Under £10k |
| SQL warehouse | Shared serverless warehouse, business hours | £10k to £20k |
| LLM next best action | About 36,000 calls a day; a smaller model or caching cuts this | £10k to £40k |
| Total |  | About £40k to £90k |


**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Small, serverless and predictable.
>
> SAY:
> If challenged on cost: it's serverless, it scales down overnight, and there's no big upfront build.

---

## 27. Root-cause rules, in priority order

- The first rule with evidence wins; no evidence goes to an analyst

| # | Root cause | Evidence | Who acts |
|---|---|---|---|
| 1 | Planned range exit | The line is exiting the store's range | No action needed |
| 2 | Market-wide shortage | The allocation was cut for a market shortage | Substitute |
| 3 | Delivery arrived short | Delivered less than ordered | Depot and buying |
| 4 | Order blocked or cancelled | The latest order status is blocked or cancelled | Depot |
| 5 | Phantom stock | A stock count removed stock that wasn't there | Store |
| 6 | Waste | Units written off | Store and buying |
| 7 | Sold more than forecast | Sales above forecast | Ordering team |
| 8 | Not yet known | No evidence | Analyst |


**Speaker notes**

> TIMING: On demand
> KEY MESSAGE: Deterministic, explainable rules, in a fixed order.
>
> SAY:
> Upstream causes come first, then store causes, then demand. The rule that fired is the explanation a colleague sees.
