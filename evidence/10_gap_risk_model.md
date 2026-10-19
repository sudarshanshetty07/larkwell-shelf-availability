# Machine learning: the gap-risk model

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

**What it predicts:** the day before, the chance that each ranged product-location is empty the next morning for an unplanned reason. A planned range exit is never predicted, because it's already known. The root-cause rules explain this morning; this model looks at tomorrow.

**How it runs:**
- The Lakeflow pipeline builds `ml.gap_risk_features`: 34 features per product-location per day, from that day's feeds and the six days before. Training and scoring read the same table.
- `ml/01_train_gap_risk.py` trains LightGBM on three weeks and tests on the following week, which it never sees. It logs to MLflow, registers the model in Unity Catalog as `ml.gap_risk`, and moves the `champion` alias only if every gate passes. The `gap_risk_training` job reruns it weekly.
- In the daily job, `ml/02_score_gap_risk.py` first grades yesterday's predictions against this morning's shelves (`ops.gap_risk_grades`). It then scores every ranged line for tomorrow with the champion, and writes each store's watch list with plain-English reasons from the model's own per-feature contributions (`ml.gap_risk_scores`).

## The model in Unity Catalog

- Registered model `larkwell_osa.ml.gap_risk`: Larkwell Foods (fictitious) gap-risk model: the probability that a ranged product-location is empty tomorrow morning for an unplanned reason, from ml.gap_risk_features. Trained by ml/01_train_gap_risk.py; scored daily by ml/02_score_gap_risk.py. The champion alias is moved only by a version that passes every gate. Synthetic data.
- Champion: version 2, from MLflow run `f7ba0a00d81c4106b0099313675ec29d`, 169 trees
- Version description: Trained on 2026-09-21 to 2026-10-11, tested on the unseen week 2026-10-12 to 2026-10-18. AUC 0.926 (today rule 0.835); top-25 watch list 60% empty next morning (today rule 46%); lines that look fine tonight 12.4% (lowest-cover rule 2.2%). Gates passed.
- Aliases: champion -> v2

### Every version

| version | aliases | registered (UTC) | description |
|---|---|---|---|
| 1 | none | 2026-10-19 01:44 | Trained on 2026-09-21 to 2026-10-11, tested on the unseen week 2026-10-12 to 2026-10-18. AUC 0.926 (today rule 0.835); top-25 watch list 60% empty next morning (today rule 46%); lines that look fine tonight 12.4% (lowest-cover rule 2.2%). Gates passed. |
| 2 | champion | 2026-10-19 02:04 | Trained on 2026-09-21 to 2026-10-11, tested on the unseen week 2026-10-12 to 2026-10-18. AUC 0.926 (today rule 0.835); top-25 watch list 60% empty next morning (today rule 46%); lines that look fine tonight 12.4% (lowest-cover rule 2.2%). Gates passed. |

Version 1 was trained by the backfill's first training attempt, which registered it and made it champion, then failed while publishing its evaluation to `ops.gap_risk_evaluations`: Spark rejected a pandas timestamp without a time zone. The automatic retry would have hit the same bug, so it was cancelled. After the fix, the repaired run trained the next version on the same data, and it had to be no worse than champion version 1 on the same test week before it took the alias. The figures below are that run's.

## The history it learns from

Training uses 2026-09-21 to 2026-10-11; the test week is 2026-10-12 to 2026-10-18. Each day's label is the next morning's shelf, joined on at training time, so nothing from the future is in the features. The first days are warm-up, to give every training day a full 7-day history.

| d | day | used for | ranged | empty_unplanned | low | empty_next_morning |
|---|---|---|---|---|---|---|
| 2026-09-14 | Mon | warm-up | 5,239,459 | 90,613 | 70,639 | 87,314 |
| 2026-09-15 | Tue | warm-up | 5,238,172 | 88,187 | 69,861 | 80,035 |
| 2026-09-16 | Wed | warm-up | 5,239,875 | 80,899 | 65,135 | 81,755 |
| 2026-09-17 | Thu | warm-up | 5,240,022 | 82,615 | 65,991 | 85,217 |
| 2026-09-18 | Fri | warm-up | 5,240,625 | 86,142 | 67,711 | 85,040 |
| 2026-09-19 | Sat | warm-up | 5,237,113 | 85,915 | 69,114 | 90,898 |
| 2026-09-20 | Sun | warm-up | 5,237,985 | 91,891 | 72,049 | 93,493 |
| 2026-09-21 | Mon | train | 5,240,633 | 94,534 | 72,304 | 84,932 |
| 2026-09-22 | Tue | train | 5,240,100 | 85,775 | 67,690 | 80,970 |
| 2026-09-23 | Wed | train | 5,237,851 | 81,779 | 66,507 | 79,654 |
| 2026-09-24 | Thu | train | 5,238,510 | 80,493 | 65,492 | 82,750 |
| 2026-09-25 | Fri | train | 5,240,458 | 83,706 | 66,462 | 88,071 |
| 2026-09-26 | Sat | train | 5,238,966 | 89,024 | 70,077 | 87,005 |
| 2026-09-27 | Sun | train | 5,238,206 | 87,926 | 69,777 | 91,806 |
| 2026-09-28 | Mon | train | 5,239,251 | 92,844 | 72,006 | 84,947 |
| 2026-09-29 | Tue | train | 5,240,582 | 85,807 | 67,568 | 79,955 |
| 2026-09-30 | Wed | train | 5,237,157 | 80,795 | 66,328 | 80,645 |
| 2026-10-01 | Thu | train | 5,241,819 | 81,571 | 64,685 | 83,229 |
| 2026-10-02 | Fri | train | 5,239,966 | 84,016 | 66,826 | 87,688 |
| 2026-10-03 | Sat | train | 5,241,769 | 88,623 | 68,563 | 88,105 |
| 2026-10-04 | Sun | train | 5,239,362 | 89,011 | 69,833 | 91,693 |
| 2026-10-05 | Mon | train | 5,238,701 | 92,685 | 72,146 | 86,335 |
| 2026-10-06 | Tue | train | 5,237,967 | 87,232 | 69,485 | 78,728 |
| 2026-10-07 | Wed | train | 5,239,096 | 79,522 | 64,718 | 80,405 |
| 2026-10-08 | Thu | train | 5,238,704 | 81,295 | 65,883 | 82,011 |
| 2026-10-09 | Fri | train | 5,238,428 | 82,882 | 66,893 | 85,871 |
| 2026-10-10 | Sat | train | 5,239,217 | 86,790 | 68,694 | 91,542 |
| 2026-10-11 | Sun | train | 5,237,006 | 92,533 | 72,808 | 92,977 |
| 2026-10-12 | Mon | test | 5,237,353 | 93,976 | 73,417 | 86,979 |
| 2026-10-13 | Tue | test | 5,237,946 | 87,885 | 69,779 | 78,222 |
| 2026-10-14 | Wed | test | 5,237,728 | 78,987 | 64,959 | 80,329 |
| 2026-10-15 | Thu | test | 5,238,748 | 81,219 | 65,775 | 81,376 |
| 2026-10-16 | Fri | test | 5,238,066 | 82,200 | 66,618 | 85,210 |
| 2026-10-17 | Sat | test | 5,238,747 | 86,142 | 68,503 | 89,457 |
| 2026-10-18 | Sun | test | 5,238,917 | 90,381 | 70,762 | 92,356 |
| 2026-10-19 | Mon | scored for tomorrow | 5,240,100 | 93,319 | 72,069 |  |

## Data checks before training

| check | value | passed | what |
|---|---|---|---|
| calendar_days_missing | 0 | true | 2026-09-15 to 2026-10-19 |
| days_reconciled | 35 | true | rows match the manifest; gaps and lows match the answer key |
| test_week_gap_rate | 1.6% | true | share of ranged lines empty the next morning |
| training_examples | 5,036,332 | true | 1,789,319 positives |

## The unseen test week: the model against the rules a store already has

Two rules use only what a store sees in the morning report: what's empty or low today (least stock first), and lowest stock against forecast. The watch list is each store's top 25 lines, every day of the test week.

| measure | model | today rule | lowest-cover rule |
|---|---|---|---|
| AUC, every ranged line | 0.926 | 0.835 | 0.833 |
| Average precision, every ranged line | 37.2% | 26.9% | 26.3% |
| Watch list: share of next morning's empty shelves it caught | 15.9% | 12.1% | 12.1% |
| Watch list (top 25 per store): share empty next morning | 59.9% | 45.7% | 45.7% |
| Brier score (lower is better) | 0.012 |  |  |
| Mean predicted risk vs observed rate (relative gap) | 2.3% |  |  |
| AUC, lines that look fine today | 0.859 | 0.661 | 0.661 |
| Average precision, lines that look fine | 5.6% | 1.3% | 1.3% |
| Looks-fine watch list: share of their empty shelves it caught | 7.1% | 1.3% | 1.3% |
| Looks-fine watch list (top 25 per store): share empty next morning | 12.4% | 2.2% | 2.2% |

On lines that look fine today, the case where a prediction matters most, the model's watch lists were empty next morning 12.4% of the time, against 2.2% for the lowest-cover rule, and 0.8% for a line that looks fine, picked at random.

## Gates: promoted only if every one passes

| gate | value | passed |
|---|---|---|
| AUC at least 0.85, and 0.05 above the today rule | 0.926 | true |
| top 25 per store: at least 1.15x the better rule (45.7%) | 0.599 | true |
| mean predicted risk within 15% of the observed rate | 0.023 | true |
| lines that look fine tonight, top 25 per store: at least 2x the better rule (2.2%) | 0.124 | true |
| AUC within 0.005 of champion version 1 on the same test week (0.9257) | 0.926 | true |
| every data check passed | 4 | true |

Promoted to `champion`: true.

## Graded every morning

Each morning the daily job checks the predictions made the day before against the shelves the pipeline has just reported. The test-week mornings were replayed with the champion after training; every later morning comes from the daily run itself.

| morning | predicted_on | model_version | auc | listed_empty | listed | list_precision | fine_listed_empty | fine_listed | predicted_rate | observed_rate |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-13 | 2026-10-12 | 2 | 0.929 | 13,615 | 22,500 | 60.5% | 2,772 | 22,500 | 1.7% | 1.7% |
| 2026-10-14 | 2026-10-13 | 2 | 0.930 | 13,110 | 22,500 | 58.3% | 2,511 | 22,500 | 1.6% | 1.5% |
| 2026-10-15 | 2026-10-14 | 2 | 0.926 | 13,342 | 22,500 | 59.3% | 2,847 | 22,500 | 1.6% | 1.5% |
| 2026-10-16 | 2026-10-15 | 2 | 0.926 | 13,341 | 22,500 | 59.3% | 2,627 | 22,500 | 1.6% | 1.6% |
| 2026-10-17 | 2026-10-16 | 2 | 0.925 | 13,620 | 22,500 | 60.5% | 3,007 | 22,500 | 1.6% | 1.6% |
| 2026-10-18 | 2026-10-17 | 2 | 0.922 | 13,608 | 22,500 | 60.5% | 2,816 | 22,500 | 1.7% | 1.7% |
| 2026-10-19 | 2026-10-18 | 2 | 0.921 | 13,675 | 22,500 | 60.8% | 2,995 | 22,500 | 1.8% | 1.8% |

## Calibration over the graded mornings: predicted risk against what happened

| decile | lines | mean_predicted | share_empty |
|---|---|---|---|
| 1 | 3,666,751 | 0.0% | 0.0% |
| 2 | 3,666,751 | 0.0% | 0.0% |
| 3 | 3,666,751 | 0.1% | 0.1% |
| 4 | 3,666,751 | 0.1% | 0.1% |
| 5 | 3,666,751 | 0.2% | 0.2% |
| 6 | 3,666,750 | 0.3% | 0.3% |
| 7 | 3,666,750 | 0.5% | 0.5% |
| 8 | 3,666,750 | 1.1% | 1.0% |
| 9 | 3,666,750 | 1.9% | 1.9% |
| 10 | 3,666,750 | 12.4% | 12.1% |

## What it learned to rely on (share of total gain, top 15)

| feature | gain_share |
|---|---|
| is_gap | 30.9% |
| exception_days_7d | 18.2% |
| fill_ratio | 16.9% |
| days_of_cover | 16.7% |
| gap_days_7d | 3.3% |
| on_hand | 2.9% |
| gap_yesterday | 2.8% |
| is_low | 1.5% |
| presentation_min | 1.1% |
| short_days_7d | 0.9% |
| waste_units | 0.7% |
| short_units | 0.4% |
| shelf_capacity | 0.4% |
| supplier_short_rate_today | 0.3% |
| supplier_short_rate_3d | 0.3% |

## Today's watch list at Covent Garden, for 2026-10-20

5,240,100 ranged product-locations scored. Lines that look fine now:

| rank | product | category | chance empty % | why |
|---|---|---|---|---|
| 1 | Orange Squash 1L | Beverages | 12.0 | Empty on 6 of the last 7 days; Empty yesterday, refilled today |
| 2 | Organic Feta 200g | Dairy | 12.0 | Empty yesterday, refilled today; Selling faster than forecast |
| 3 | Coronation Chicken Sandwich 2pk Family Pack | Sandwiches & Food To Go | 11.0 | Empty on 2 of the last 7 days; Empty yesterday, refilled today; Short deliveries on 2 of the last 7 days |
| 4 | Whole Milk 4 pints Family Pack | Dairy | 10.0 | Empty on 3 of the last 7 days; Empty yesterday, refilled today; Only 3 left on the shelf |
| 5 | Organic Wholemeal Loaf 400g | Bakery | 9.0 | Shelf only 33% full; Empty yesterday, refilled today; Only 2 left on the shelf |
| 6 | Granary Cob 400g | Bakery | 9.0 | An order is blocked at the depot; Only 3 left on the shelf |
| 7 | Frozen Vegetable Samosas 16pk Multi-Buy | Frozen | 9.0 | Empty yesterday, refilled today; Only 2 left on the shelf; On promotion |
| 8 | Butternut Squash Soup 400g 2 for £5 | Sandwiches & Food To Go | 9.0 | Empty yesterday, refilled today; On promotion; Short shelf life (1 day) |
| 9 | Organic Earl Grey Tea 50 bags | Beverages | 8.0 | Shelf only 38% full; Today's delivery came 2 short |
| 10 | All-Butter Croissants 4pk Multi-Buy | Bakery | 8.0 | Empty on 2 of the last 7 days; A stock count found 5 units that weren't there; Only 3 left on the shelf |

Today's gaps and lows most likely to still be empty tomorrow:

| rank | product | this morning | chance empty % | why |
|---|---|---|---|---|
| 1 | Easy Peeler Clementines 600g Multi-Buy | GAP | 77.0 | Empty this morning; Empty on 7 of the last 7 days; Empty yesterday too |
| 2 | Radishes 400g Multi-Buy | GAP | 77.0 | Empty this morning; Empty on 7 of the last 7 days; Empty yesterday too |
| 3 | Parmesan 200g 2 for £5 | GAP | 75.0 | Empty this morning; Empty or low on 7 of the last 7 days; Empty yesterday too |
| 4 | Roast Chicken Dinner 400g | GAP | 72.0 | Empty this morning; Empty on 5 of the last 7 days; Empty yesterday too |
| 5 | Breakfast Tea 80 bags Value Pack | GAP | 70.0 | Empty this morning; Empty on 7 of the last 7 days; Empty yesterday too |
