# How AI was used to build this

The whole build was done in one working session with **Claude Code**, Anthropic's agentic coding tool, working in the
terminal against a Databricks workspace. The conversation ID is in the submission form.

## Division of labour

| The person (field engineer) decided | The AI did |
|---|---|
| Which business problem to build on: availability root cause for a large UK food retailer | Assessed five earlier builds against the brief and recommended this one, with the gaps to close |
| The workspace, the public repo, how far to take the AI stage | Designed the end-to-end architecture and the data model |
| That everything must be synthetic and free of customer content | Wrote the generator, 27 pipeline files, the app changes, the Genie space, the evaluation, the gap-risk model, the bundle and the tests |
| To add a trained model after asking "Did we use an ML model?", and accepted that the generator, pipeline, evidence, deck and docs would change | Proposed the model that fits the data (tomorrow's gap risk), found the blocker (every simulated day shared one seed), designed the history so the demo day stayed exact, and built it end to end |
| Approval before anything outward-facing, such as pushing to GitHub | Ran every step, read the results, and fixed what broke |

## Working patterns that made it reliable

1. **Answer key first.** Before writing the pipeline, the AI designed the generator to write an answer key the pipeline never reads. Every run since proves the root-cause logic row by row (205,834 of 205,834).
2. **Dry-run locally, then run in the cloud.** The generator ran on the laptop in 39 seconds before its first serverless run, with a pandas re-implementation of the rules as a self-check.
3. **Product skills as guardrails.** Databricks' own agent skills were loaded before each product was touched, for pipelines, Lakebase, apps, Genie, metric views, jobs and bundles. That gave the exact syntax and the constraints, for example:
   - synced tables accept materialized views;
   - Lakehouse Sync needs Postgres 17 and `REPLICA IDENTITY FULL`;
   - every metric-view `format` block needs a `type`.
4. **Checked edits.** Changes to large files were applied as patches where every replacement must match exactly once, so nothing is half-edited.
5. **Evidence as code.** `scripts/collect_evidence.py` regenerates every file in `evidence/` from the live workspace, and `scripts/e2e_test.py` tests the deployed app.
6. **A publish gate.** A local scan blocks the push if it finds customer references, hostnames, emails or tokens.
7. **Change the past without moving the demo.** Before the generator gained history, the AI downloaded the anchor day's 23
   raw files and its answer key from the workspace, refactored the generator, and regenerated the day locally. Every file
   matched byte for byte, so every number in the deck still held.
8. **Calibrate at full scale on the laptop first.** Five weeks of history (35 days of 5.4 million product-locations) were
   simulated locally, and a LightGBM prototype was measured against the rules, before anything reached the workspace. Four
   calibration rounds took about 25 minutes; each workspace round would have taken over an hour.
9. **Validate the pipeline before the long run.** A validate-only pipeline update checks every dataset's SQL and schema
   in about a minute. It caught a type error before the hour-long rebuild of 36 days.

## What the AI caught and fixed along the way

| Found | How | Fix |
|---|---|---|
| The first synthetic sales base was about £24bn a year, roughly three times a realistic UK food retailer | Checked the metric view's totals against the business | Recalibrated demand to about £8.2bn; quantities rescaled to store-line size |
| Stock-count, waste and allocation IDs restart every day, so silver dropped day two's evidence | Ran a second business day through the daily job; the checks failed | De-duplicate within each business day; the checks now cover every expected cause |
| An LLM judge demanded "one action" while the playbook deliberately gives two-step actions | Read the judges' reasoning per case | Corrected the guideline to the real requirement |
| The judge then marked advice down for codes that appeared only in the raw input row, never in the advice | Judges' reasoning again | The judge now sees exactly the plain-English facts the model saw; actionability is checked exactly by code |
| The no-contradiction check flagged "don't chase the supplier or try to reorder" | Per-case results | Negation is checked across the whole sentence, not four words |
| On a new trading day, the judge read depot names such as "Merseyvale DC" as codes, then marked correct advice down for not naming the store | The daily job failed; the judges' reasoning per case | The guideline says what not to judge. A calibration set of hand-labelled good and bad answers proves on every run that the judges still fail bad advice |
| The consistency judge treated leaving part of the action out as a contradiction, even though its guideline said it isn't | The daily job failed again; compared three judge models on the calibration set | Both judges moved to GPT-5.5, a different family from the advice model. It agreed with every label; the default judge didn't |
| The stricter judge then caught two real defects the default judge had missed: two replies opened with a markdown heading, and the playbook's own word "expedite" read as corporate | Judges' reasoning per case; replayed all 48 cases locally before re-running the job | Prompt v4 forbids a title, the playbook says "speed it up", and the app strips any markup before display |
| The prompt produced "1 units", a markdown heading, and guessed causes | MLflow evaluation | Prompt v3: unit grammar, plain sentences only, only what the facts say |
| Genie split a "how many" into rows, and copied a ranked example for a top-1 question | Genie benchmark (11 of 12) | Two general instructions and a reworded example: 12 of 12 |
| A job repair wasn't given the business date, so it checked the default day against the next day's gold, and passed because the synthetic days share a seed | Reconciling the check history with the job runs while writing the evidence | Validation now refuses to check a different day from the one gold holds; the evidence marks that pass as not counting |
| Re-landing a day gave different quantities on the same shelves: `np.argpartition` order varies by CPU | Daily checks (answer key no longer matched) | Sorted the selection; two runs now give byte-identical answer keys |
| A connection-pool bug: Postgres connection objects don't allow extra attributes | Smoke test (the app fell back to the warehouse, as designed) | Tracked connection age separately |
| Every simulated trading day used the same seed, so every day showed the same exceptions. A model trained on that would learn nothing real | Asked whether the build used an ML model; checked whether the data could support one | A day-to-day process around one pinned anchor day (`docs/decisions.md` §16) |
| In the first calibration only 29% of today's gaps were still empty tomorrow. Real shelves persist more | Measured persistence in the local simulation before building the model | Raised the day-to-day persistence to give 47% |
| The prototype model leaned on today's status and stock cover and barely used the warning signs, which looked like a simulation fault | Feature importance, then a diagnostic of the next-day gap rate after each kind of signal | The signs were fine: each makes a gap tomorrow 3 to 8 times more likely than on a healthy shelf, but they touch few lines. Tying thin shelves to store-side causes only had made stock cover nearly useless (1.5 times), so cover was restored for every cause except planned exits (2.5 times for the thinnest 1%) |
| Spark averages decimal literals (`1.0`, `0.0`) into a DECIMAL, which clashed with the features table's declared DOUBLE | A validate-only pipeline update, before the 36-day rebuild | Cast the averages to DOUBLE |
| Re-running `governance/after_pipeline.sql` (to tag the new features table) inserted the three demo app users a second time | Checked the roles table straight after the run | The script now uses a MERGE, so it's safe to re-run; the duplicates were removed |
| Some reasons on the watch list weren't true for the line: "Empty yesterday as well" on a shelf that was fine yesterday, because a feature's contribution can be positive even at zero | Read the first replayed day's watch list for Covent Garden | Each reason now has a condition on the line's own value, and thresholds sit well above the typical value. The affected days were re-scored. (One-off runs started on an older serverless environment and hit a pandas bug, so the re-scores ran through the daily job's own task instead) |
| The first training run registered version 1 and made it champion, then failed while writing its evaluation: Spark rejects a pandas timestamp without a time zone | The job failed; read the error trace. The job then retried on its own | Cancelled the retry, which would have hit the same bug. Timestamps are now plain Python datetimes. In the repaired run, version 2 had to be no worse than champion version 1 on the same test week before it took the alias (it matched it exactly: same data, same seed) |
| The query CLI collapses whitespace, which broke the metric view's YAML | Deployment error | Statement API helper (`scripts/run_sql_file.py`) |
| The original app padded pinned answers to 6-8 seconds to look like an agent "thinking", and showed hard-coded risk windows | Code review before reuse | Removed the delay and labelled curated answers as such; the risk window is now worked out from stock and forecast |

## Representative prompts

- "Review the guidelines and tell me which use case I've built previously aligns closest, so you can extend it."
- "Clarify all the questions before you start building, so the demo and roleplay deck are solid."
- The AI's clarifying questions (use case, workspace, repo, AI scope) and the person's answers are in the conversation.
