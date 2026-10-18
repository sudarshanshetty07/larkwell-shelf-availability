# How AI was used to build this

The whole build was done in one working session with **Claude Code**, Anthropic's agentic coding tool, working in the
terminal against a Databricks workspace. The conversation ID is in the submission form.

## Division of labour

| The person (field engineer) decided | The AI did |
|---|---|
| Which business problem to build on: availability root cause for a large UK food retailer | Assessed five earlier builds against the brief and recommended this one, with the gaps to close |
| The workspace, the public repo, how far to take the AI stage | Designed the end-to-end architecture and the data model |
| That everything must be synthetic and free of customer content | Wrote the generator, 25 pipeline files, the app changes, the Genie space, the evaluation, the bundle and the tests |
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
| The query CLI collapses whitespace, which broke the metric view's YAML | Deployment error | Statement API helper (`scripts/run_sql_file.py`) |
| The original app padded pinned answers to 6-8 seconds to look like an agent "thinking", and showed hard-coded risk windows | Code review before reuse | Removed the delay and labelled curated answers as such; the risk window is now worked out from stock and forecast |

## Representative prompts

- "Review the guidelines and tell me which use case I've built previously aligns closest, so you can extend it."
- "Clarify all the questions before you start building, so the demo and roleplay deck are solid."
- The AI's clarifying questions (use case, workspace, repo, AI scope) and the person's answers are in the conversation.
