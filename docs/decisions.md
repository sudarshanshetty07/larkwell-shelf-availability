# Decisions and trade-offs

Each decision lists the option chosen, the main alternative, and why.

## 1. Root cause is a rules cascade, not a model
- **Chosen:** eight evidence checks in a fixed priority order, written in SQL in the gold layer. Upstream causes come first, then store causes, then demand (`pipeline/gold/product_location_status.sql`).
- **Alternative:** a classifier trained on labelled gaps.
- **Why:** a store colleague and an availability analyst both need to know *why* a line is flagged, and the rule that fired is the explanation. It's deterministic, auditable, and testable row by row against the answer key (205,834 of 205,834 match). It attributes 98% of gaps and lows; the remaining 2% are flagged INVESTIGATE rather than guessed. Machine learning is used where it beats rules: predicting which lines will be empty *tomorrow* (§14).

## 2. Lakeflow Spark Declarative Pipelines, written in SQL
- **Chosen:** 27 small SQL files, one dataset per file. Bronze streaming tables use Auto Loader; silver, gold and the model's features are materialized views.
- **Alternative:** notebooks with hand-written merge logic.
- **Why:**
  - lineage, expectations and incremental ingestion come built in;
  - the logic stays readable by an analyst;
  - Auto Loader only reads new files, so day two ingested just day two's 23 files.
- **Trade-off:** materialized views recompute fully when their inputs change. Gold is 5.4M rows; the stock history and the model's features hold six weeks (about 200M rows), which is what makes the daily update take minutes rather than seconds. At much larger scale I'd make gold and the features incremental (§15).

## 3. Lakebase for Shelf Scan, the warehouse for analytics
- **Chosen:** Unity Catalog syncs the gold table into Lakebase. Shelf Scan does a primary-key lookup there, and dashboards query the warehouse.
- **Alternative:** serve everything from the SQL warehouse.
- **Why:** a handheld scan is an OLTP point lookup, made by thousands of colleagues at once.
  - Measured inside the app, Lakebase answers in 2.5 ms at the median; the warehouse takes 634 ms for the same row, 259 times slower. Across test runs it has ranged from about 2 to 3 ms against 0.5 to 0.7 s: well over 100 times faster every time.
  - The warehouse stays as a fallback, so a scan always answers.
- **Trade-off:** a second copy of the data. It's a governed, read-only synced copy that Unity Catalog manages, so it can't drift.

## 4. Daily snapshot sync, not continuous
- **Chosen:** a snapshot synced table, refreshed by the daily job (5.4M rows in about 3 minutes at 1-8 CU; see the refresh task in `evidence/09_daily_job_runs.md`).
- **Alternative:** triggered or continuous sync with Change Data Feed.
- **Why:** stock positions arrive once a day, so continuous sync would cost more and add nothing. Continuous becomes worthwhile when stock feeds become intraday.

## 5. The app writes to Lakebase, not to Delta
- **Chosen:** colleague actions, scan telemetry, AI recommendations and Genie feedback go to Postgres. Lakehouse Sync streams every change back to Unity Catalog, where governed views expose them without personal data.
- **Alternative:** write directly to Delta tables through the warehouse.
- **Why:**
  - transactional writes in milliseconds;
  - the app needs no write access to the lakehouse at all, because its service principal is read-only in Unity Catalog;
  - the full change history lands in Unity Catalog for Genie and reporting.
- **Trade-off:** Lakehouse Sync is in Beta. If it weren't available, a federated query over the Lakebase catalog would serve the same views.

## 6. The LLM words the advice; it never decides it
- **Chosen:** the root cause comes from the rules and the action from a fixed playbook, and every number is passed in as a sentence. The model only phrases it for a colleague (`app/nba.py`). If the model is down, a template answers.
- **Guard:** the prompt forbids headings and markup, but the model occasionally added a title anyway, so the app removes any markup before display (`nba.clean`). The evaluation scores that cleaned text: exactly what the colleague sees.
- **Alternative:** let the model reason from raw columns.
- **Why:** an earlier version passed raw columns, and the model rounded numbers, invented units such as "cases", and misread codes. The evaluation now checks that every number in the advice appears in the facts, and that the advice follows the playbook and never contradicts it.

## 7. Evaluate the AI on every run, with code checks and calibrated LLM judges
- **Chosen:** an MLflow GenAI evaluation of the app's own prompt on 48 real cases, with six deterministic checks and two LLM judges. Before scoring, the judges grade 19 hand-labelled answers, good and deliberately bad, and must agree with every label. The judges run on GPT-5.5, a different model family from the one that writes the advice (Claude Sonnet 4.5). Thresholds fail the daily job.
- **Why:** the evaluation found real issues: "1 units", a markdown heading, guessed causes. It also found five faults in the evaluation itself:
  - a judge that demanded "one action" when the playbook deliberately gives two-step actions;
  - a judge that marked advice down for codes it saw only in the raw input row;
  - a negation window that was too short in the no-contradiction check;
  - on a new trading day, a judge that read depot names as codes, then marked correct advice down for not naming the store;
  - a consistency judge that treated leaving part of the action out as contradicting it. Its guideline said otherwise, but the default judge model didn't follow it, so the judges moved to a model that does, and the calibration set proves it.
- **Design rule that came out of it:** use code checks for anything exactly checkable (numbers, playbook action, contradictions, units, codes, length). Use LLM judges only for qualities that need judgement. Tell them what not to judge, show them exactly what the model saw, run them on a different model family, and calibrate them against hand labels on every run. Loosening a judge is only safe if you can prove it still fails bad answers. No threshold was lowered to get a pass.
- **Result:** the final run (prompt v4, judges on GPT-5.5) scores 100% on all eight checks, and both judges agree with all 19 calibration labels. The full run history is in `evidence/08_genai_evaluation.md`.

## 8. Genie over a governed metric view
- **Chosen:** a metric view defines availability, gap rate, attribution, actionable gaps and sales at risk once. Genie uses it alongside gold and the actions views, with 9 example queries.
- **Why:** finance, buying and stores get the same numbers. The benchmark went from 11 to 12 out of 12. Both fixes were general instructions, not copied answers.

## 9. Curated analyses for the three headline questions
- **Chosen:** the three suggested questions run fixed, tested SQL and are labelled "curated analysis" in the app. Anything else goes to Genie.
- **Why:** the questions shown in a demo or a morning meeting must never vary. Free-form questions show Genie's flexibility, and both kinds of answer are labelled honestly.

## 10. Synthetic data with an answer key
- **Chosen:** a seeded generator plays the source systems and writes an answer key the pipeline never reads. One anchor day is pinned, and the days around it vary (§16).
- **Alternative:** a public dataset.
- **Why:** no public dataset has store-by-line availability with root causes. The answer key lets the build *prove* the pipeline is right on every run.
  - Realistic noise is built in: 29% of exceptions carry more than one kind of evidence, and there are re-sent duplicates, malformed records and master-data corrections.
  - The sales base is calibrated to about £8.2bn a year, the scale of a large UK food retailer.

## 11. Security and governance
- The app's service principal can read only gold and ops, and can't write to the lakehouse.
- In Lakebase it can read the serving table and read, insert and update its own tables, with no deletes.
- Governed tags carry the workspace's own tag-policy values: `data_classification` set to internal, confidential or pii, and a domain tag.
- User emails stay in one restricted table, tagged pii, and every view built for Genie leaves them out.

## 12. Found by testing more than one day
Running a second business day showed that the source systems' stock-count, waste and allocation IDs restart every day. Silver was de-duplicating on the ID alone, so day two's evidence was dropped. Silver now de-duplicates within each business day. The daily checks caught it (`evidence/09_daily_job_runs.md` shows the failed attempt and the repair). The same run exposed a gap in the checks themselves: they now cover every expected root cause, even one whose count falls to zero.

## 13. Re-running a day exposed a reproducibility bug
Re-landing a trading day that had already been ingested taught two things.
- **Auto Loader skips files it has already seen, even if they're rewritten.** That's correct behaviour. A source system re-sending a day must use new file names, or the day needs a full refresh.
- **The generator wasn't reproducible across machines.** `np.argpartition` returns the chosen shelves in an order that varies by CPU, and quantities were assigned by position, so a re-run put different quantities on the same shelves.
  - The daily checks caught it (only 45,800 of 205,834 matched the regenerated answer key).
  - Sorting the selection fixed it, and two runs now produce byte-identical answer keys.

The evidence keeps both failed runs, so the record shows what the checks are for.

## 14. Predicting tomorrow's gaps: a gradient-boosted model, judged against the rules a store already has
- **Chosen:** LightGBM, predicting the day before whether each ranged product-location will be empty the next morning for an unplanned reason. It uses 34 features (`ml/gap_risk.py`), is trained on three weeks and tested on the following week, which it never sees. It's logged to MLflow and registered in Unity Catalog as `ml.gap_risk`.
- **Alternatives:** a time-series forecast of every line's stock, or a deep sequence model.
- **Why:**
  - The question is a yes or no about tomorrow morning, asked of 5.4 million product-locations every day. Gradient-boosted trees on tabular features are the standard tool for that: fast to train and score, and robust to the mix of counts, rates and flags.
  - Every prediction comes with its reasons. The model's own per-feature contributions (SHAP values) are turned into plain English ("Today's delivery came 6 short", "Empty on 3 of the last 7 days"), so a store sees why a line is on its list.
  - It isn't compared with chance. It has to beat the two rules a store could use without it: what's empty or low this morning, and lowest stock against forecast.
- **What it's not:** it doesn't replace the root-cause rules. The rules explain this morning, row by row; the model ranks tomorrow's risk. A planned range exit is never predicted, because it's already known.
- **Gates:** a new version takes the `champion` alias, which the daily job scores with, only if:
  - it beats both rules by set margins;
  - its probabilities are calibrated;
  - it's no worse than the current champion on the same test week;
  - every data check passed.
  A version that fails is registered as `challenger` and never scored.
- **Graded every morning:** the daily job checks yesterday's predictions against the shelves the pipeline has just reported, before it makes today's (`ops.gap_risk_grades`). So the model is marked every day, not only when it's trained.
- **Trade-off:** it's trained on simulated history, so its accuracy here only proves the method works. The pilot retrains it on real history, and measures the share of gaps prevented against control stores.

## 15. Features in the pipeline, labels outside it
- **Chosen:** the Lakeflow pipeline builds `ml.gap_risk_features`: one row per product-location per day, from that day's feeds and the six days before. Training joins on the label, the next morning's shelf, at training time. Scoring reads today's rows.
- **Alternative:** compute features in the training notebook and again in the scoring notebook.
- **Why:**
  - **One definition.** Training and scoring use the same features, so they can't drift apart.
  - **No leakage.** Nothing from the future can reach the model, because the label never goes into the features table.
  - **Governed like gold.** The features get expectations, lineage, tags and the daily checks. For example, today's count of unplanned gaps in the features must equal gold's.
- **Trade-off:** the features table is recomputed every day over six weeks of history. That's a few minutes on serverless. In production I'd keep the history in a feature table appended once a day, and use Unity Catalog's feature engineering for point-in-time lookups.

## 16. History: one pinned day, and a day-to-day process around it
- **Problem:** every simulated trading day used the same seed, so every day showed the same exceptions. A model trained on that would learn nothing real.
- **Chosen:** the anchor day, 19 October 2026, stays pinned. Its headline counts are exact, and the generator reproduces it byte for byte, so the business case and every earlier piece of evidence still hold. Any other date is the anchor rolled one day at a time (`data/01_land_raw_feeds.py`):
  - **Trouble carries over.** Each product-location has a hidden score for each cause, which drifts a little each day: a first-order autoregressive process, started from the anchor's own random draws. Each day's exceptions are still the lines with the highest weight plus score, exactly as on the anchor.
  - **Good and bad spells.** Supplier, depot and store reliability drift, and market shortages come and go.
  - **Warning signs.** Lines that came close to failing get more than their share of the day's short deliveries, blocked orders, stock counts, waste and cut allocations, and thinner shelves. Most warning signs never become a gap, and many gaps come with no warning.
  - **The week.** Volumes and demand follow the day of the week.
  - **Same checks.** Every day passes the same row-by-row self-check against its own answer key.
- **How it was tuned:** to realistic persistence, not to make the model look good. About 47% of today's unplanned gaps are still empty tomorrow. A warning sign makes a gap tomorrow 3 to 8 times more likely than on a healthy shelf. Thin shelves matter, but less. The tuning used the rules as baselines, so a model can only win by learning something the rules miss.
- **Trade-off:** the model can only be as realistic as the simulation. That's why the pilot retrains it on real history before anyone relies on it.

## What production would add
- Intraday stock feeds and continuous sync.
- On-behalf-of-user auth, so Unity Catalog row filters apply per colleague.
- Lakehouse Sync out of Beta.
- For the gap-risk model:
  - a year or more of real history, with the promotions calendar and weather as features;
  - an incremental feature table;
  - drift monitoring on the inputs and the daily grades.
- Alerting on the daily checks.
- CI that runs the bundle validation and the answer-key test on every change.
