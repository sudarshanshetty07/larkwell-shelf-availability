# Lakeflow Jobs: the daily run, end to end

_Generated 2026-10-18 14:18 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

The bundle job `Larkwell shelf availability - daily run` (`resources/daily_run.job.yml`) runs the whole journey for one trading day: land the raw feeds, run the Lakeflow pipeline, refresh the Lakebase copy, check every stage, then evaluate the AI. Its schedule (05:00 Europe/London) is paused in this demo workspace.

The trading days are simulated: the job takes the business date as a parameter, so consecutive trading days were run back to back. A repair re-runs only the failed tasks. It doesn't carry run-time parameters over, so the business date has to be passed again, and validation now refuses to run if it isn't.

## Run 87621466072770: SUCCESS (business date 2026-10-19)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | evaluate_next_best_action | SUCCESS | 192s |  |
| original run | land_raw_feeds | DISABLED | 0s |  |
| original run | refresh_lakebase | DISABLED | 0s |  |
| original run | run_pipeline | DISABLED | 0s |  |
| original run | validate_and_publish | DISABLED | 0s |  |

## Run 505636645897897: FAILED (business date 2026-10-19)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | evaluate_next_best_action | FAILED | 167s | AssertionError: Below threshold: ['plain_english'] |
| original run | land_raw_feeds | DISABLED | 0s |  |
| original run | refresh_lakebase | DISABLED | 0s |  |
| original run | run_pipeline | DISABLED | 0s |  |
| original run | validate_and_publish | DISABLED | 0s |  |

## Run 50574576867157: FAILED (business date 2026-10-19)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | land_raw_feeds | DISABLED | 0s |  |
| original run | refresh_lakebase | DISABLED | 0s |  |
| original run | run_pipeline | DISABLED | 0s |  |
| original run | validate_and_publish | SUCCESS | 84s |  |
| original run | evaluate_next_best_action | FAILED | 132s | AssertionError: Below threshold: ['consistent_with_playbook'] |
| original run | evaluate_next_best_action | FAILED | 129s | AssertionError: Below threshold: ['consistent_with_playbook'] |

## Run 579644941436451: SUCCESS (business date 2026-10-19)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | evaluate_next_best_action | SUCCESS | 246s |  |
| original run | land_raw_feeds | DISABLED | 0s |  |
| original run | refresh_lakebase | DISABLED | 0s |  |
| original run | run_pipeline | DISABLED | 0s |  |
| original run | validate_and_publish | DISABLED | 0s |  |

## Run 197776924473336: SUCCESS (business date 2026-10-19)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | land_raw_feeds | SUCCESS | 112s |  |
| original run | run_pipeline | SUCCESS | 185s |  |
| original run | refresh_lakebase | SUCCESS | 185s |  |
| original run | validate_and_publish | SUCCESS | 86s |  |
| original run | evaluate_next_best_action | FAILED | 120s | AssertionError: Below threshold: ['plain_english'] |
| repair 1 | evaluate_next_best_action | SUCCESS | 169s |  |

## Run 978046411345237: FAILED (business date 2026-10-18)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | land_raw_feeds | SUCCESS | 107s |  |
| original run | run_pipeline | SUCCESS | 94s |  |
| original run | refresh_lakebase | SUCCESS | 33s |  |
| original run | validate_and_publish | FAILED | 98s | AssertionError: 4 checks failed: ['bronze.rows_waste', 'bronze.rows_allocations', 'bronze.rows_ingested', 'gold.answer_key_matches'] |
| original run | validate_and_publish | FAILED | 42s | AssertionError: 4 checks failed: ['bronze.rows_waste', 'bronze.rows_allocations', 'bronze.rows_ingested', 'gold.answer_key_matches'] |
| original run | evaluate_next_best_action | UPSTREAM_FAILED | 0s |  |

## Run 734443068835679: SUCCESS (business date 2026-10-18)

| attempt | task | result | duration | why it failed |
|---|---|---|---|---|
| original run | land_raw_feeds | SUCCESS | 74s |  |
| original run | run_pipeline | SUCCESS | 185s |  |
| original run | refresh_lakebase | SUCCESS | 185s |  |
| original run | validate_and_publish | FAILED | 91s | AssertionError: 5 checks failed: ['gold.reason_under_forecast', 'gold.reason_investigate', 'gold.reason_supplier_short', 'gold.reason_order_delivery_block', 'gold.answer_key_matches'] |
| original run | validate_and_publish | FAILED | 86s | AssertionError: 5 checks failed: ['gold.reason_under_forecast', 'gold.reason_investigate', 'gold.reason_supplier_short', 'gold.reason_order_delivery_block', 'gold.answer_key_matches'] |
| original run | evaluate_next_best_action | UPSTREAM_FAILED | 0s |  |
| repair 1 | run_pipeline | SUCCESS | 114s |  |
| repair 1 | refresh_lakebase | SUCCESS | 215s |  |
| repair 1 | validate_and_publish | SUCCESS | 76s |  |
| repair 1 | evaluate_next_best_action | FAILED | 99s | AssertionError: Below threshold: ['no_contradiction', 'plain_english', 'consistent_with_playbook'] |
| repair 1 | evaluate_next_best_action | FAILED | 153s | AssertionError: Below threshold: ['no_contradiction', 'plain_english'] |
| repair 2 | evaluate_next_best_action | FAILED | 122s | AssertionError: Below threshold: ['plain_english', 'consistent_with_playbook'] |
| repair 2 | evaluate_next_best_action | FAILED | 156s | AssertionError: Below threshold: ['plain_english', 'consistent_with_playbook'] |
| repair 3 | evaluate_next_best_action | FAILED | 123s | AssertionError: Below threshold: ['plain_english'] |
| repair 3 | evaluate_next_best_action | SUCCESS | 156s |  |

## What each failure caught

The first trading day (2026-10-17) was built and checked while the job was being written; above is every run of the finished job.
- **2026-10-18, first run:**
  - The root-cause counts and the answer key failed. The source systems' stock-count, waste and allocation IDs restart every day, and silver de-duplicated on the ID alone, so day two's evidence was dropped (`docs/decisions.md` §12).
  - Silver was fixed and the run repaired. The AI evaluation's failures in the same run are the judge and prompt fixes in `08_genai_evaluation.md`.
  - **The run's final pass doesn't count.** The repaired validation wasn't given the business date, so it checked the default, 2026-10-17, against gold for 2026-10-18. It passed only because the synthetic days share a seed. Validation now refuses to check a different day from the one gold holds, and 2026-10-18 is never claimed as passed.
- **2026-10-18, landed again:** bronze counts and the answer key failed. The generator wasn't reproducible across machines, and Auto Loader rightly skipped files it had already ingested (§13). The generator was fixed, and the next trading day was run fresh.
- **2026-10-19:** every stage passed. The AI evaluation failed on its plain-English judge; the judge was fixed and the task repaired.
- **2026-10-19, evaluation only:** the AI evaluation again, after the plain-English judge's guideline was reworded and the judges were calibrated against hand labels.
- **2026-10-19, validation and evaluation:** validation passed with the new date guard. The evaluation failed: the consistency judge marked three correct answers down for leaving part of the action out (`08_genai_evaluation.md`).
- **2026-10-19, evaluation only, again:** both judges on GPT-5.5, with those cases added to the calibration set. The stricter judge failed plain English on two real defects: replies that opened with a heading, and the playbook's 'expedite'.
- **2026-10-19, evaluation only, prompt v4:** the prompt and playbook fixed and the app's markup guard in place.
