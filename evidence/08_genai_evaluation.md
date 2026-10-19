# Gen AI: evaluation of the next best action

_Generated 2026-10-19 08:08 UTC by `scripts/collect_evidence.py` from the live workspace. Larkwell Foods is fictitious; all data is synthetic._

MLflow GenAI evaluation of the exact prompt the app uses (`app/nba.py`), on 48 real exceptions from gold (6 per root cause). Every call is traced in MLflow. Notebook: `genai/03_evaluate_next_best_action.py`; it runs as the last task of the daily job.

MLflow run `23adcc35457c484280bac8965d414c99`, prompt `nba-v4`, advice written by `databricks-claude-sonnet-4-5`, judged by `databricks:/databricks-gpt-5-5`, 48 cases.

| metric | value | threshold | passed |
|---|---|---|---|
| concise | 100.0% | 90% | true |
| consistent_with_playbook | 100.0% | 95% | true |
| follows_playbook | 100.0% | 95% | true |
| judge_calibration_consistent_with_playbook | 100.0% | 100% | true |
| judge_calibration_plain_english | 100.0% | 100% | true |
| no_contradiction | 100.0% | 100% | true |
| no_internal_codes | 100.0% | 100% | true |
| numbers_grounded | 100.0% | 98% | true |
| plain_english | 100.0% | 90% | true |
| units_only | 100.0% | 100% | true |

## How it got here: every evaluation run

Each run that failed found something real, and every fix was recorded. After the prompt fixes, every failure was a judge's mistake, found by reading its reasoning case by case. No threshold was lowered to get a pass.
- **nba-v2:** the plain-English judge demanded 'one action', but the playbook deliberately gives two-step actions. The judge was corrected.
- **nba-v3** (after the prompt fixes for '1 units', headings and guessed causes):
  - The rule-based no-contradiction check flagged negated advice ('don't ... reorder'). Its negation window was too short, so it now checks the whole sentence.
  - The judge then marked advice down for codes that only appeared in the raw input row. The evaluation now shows the judge exactly the plain-English facts the model saw.
  - Actionability is measured exactly by the code check `follows_playbook`, so the LLM judge assesses language only.
- **Day three** (a new trading day, so new cases):
  - The plain-English judge failed the run at 85%: it read depot names such as 'Merseyvale DC' as internal codes. Codes are already checked exactly by `no_internal_codes`, so the judge was narrowed to tone and wording.
  - The repaired run passed at 92%, but all four failures were still the judge's mistakes: it marked correct advice down for not naming the store, and for not using the phrase 'phantom stock'. The guideline now says what not to judge, and a calibration set (below) proves on every run that both judges still fail bad advice.
  - The consistency judge then marked three correct answers down: two for leaving out 'no supplier chase is needed', one for adding 'ask your manager'. Its guideline already said that leaving something out isn't a contradiction, but the default judge model didn't follow it. Both judges now run on GPT-5.5, a different model family from the one that writes the advice, and those cases joined the calibration set.
- **nba-v4:** the stricter judge caught two real defects the default judge had missed. Two replies opened with a markdown heading, and the playbook's own word 'expedite' read as corporate. The prompt now forbids a title, the playbook says 'speed it up', and the app removes any markup before display (`nba.clean`). The evaluation scores that cleaned text.

| evaluated (UTC) | prompt_version | numbers_grounded | follows_playbook | no_contradiction | plain_english | consistent_with_playbook | result |
|---|---|---|---|---|---|---|---|
| 2026-10-18 11:54:50 | nba-v2 | 100% | 100% | 100% | 27% | 88% | below threshold |
| 2026-10-18 11:57:36 | nba-v2 | 100% | 100% | 100% | 19% | 85% | below threshold |
| 2026-10-18 12:13:05 | nba-v3 | 100% | 100% | 96% | 44% | 92% | below threshold |
| 2026-10-18 12:15:39 | nba-v3 | 100% | 100% | 94% | 52% | 100% | below threshold |
| 2026-10-18 12:19:32 | nba-v3 | 100% | 100% | 100% | 79% | 92% | below threshold |
| 2026-10-18 12:22:14 | nba-v3 | 100% | 100% | 100% | 67% | 83% | below threshold |
| 2026-10-18 12:28:09 | nba-v3 | 100% | 100% | 100% | 85% | 96% | below threshold |
| 2026-10-18 12:30:52 | nba-v3 | 100% | 98% | 100% | 92% | 98% | all thresholds met |
| 2026-10-18 13:00:08 | nba-v3 | 100% | 100% | 100% | 85% | 98% | below threshold |
| 2026-10-18 13:04:18 | nba-v3 | 100% | 100% | 100% | 92% | 100% | all thresholds met |
| 2026-10-18 13:31:16 | nba-v3 | 100% | 100% | 100% | 100% | 98% | all thresholds met |
| 2026-10-18 13:41:39 | nba-v3 | 100% | 100% | 100% | 100% | 94% | below threshold |
| 2026-10-18 13:43:52 | nba-v3 | 100% | 100% | 100% | 100% | 94% | below threshold |
| 2026-10-18 14:00:47 | nba-v3 | 100% | 100% | 100% | 90% | 100% | below threshold |
| 2026-10-18 14:08:46 | nba-v4 | 100% | 100% | 100% | 100% | 100% | all thresholds met |
| 2026-10-19 02:40:19 | nba-v4 | 100% | 100% | 100% | 100% | 100% | all thresholds met |

## Judge calibration (this run)

Before scoring, each LLM judge grades fixed answers labelled by hand: good ones, and bad ones written to show the failures each judge exists to catch. It must agree with every label, or the job fails.

| judge | human_label | judge_verdict | agrees | answer |
|---|---|---|---|---|
| consistent_with_playbook | yes | yes | True | The order for this line is blocked at Merseyvale DC, so nothing can reach the shelf. Ask the depot to release the blo... |
| consistent_with_playbook | yes | yes | True | The order for this line is blocked at Merseyvale DC, so nothing has arrived. Ask the depot to release the blocked ord... |
| consistent_with_playbook | yes | yes | True | The shelf is empty because 7 units were written off as waste. Check the date codes and handling, then ask your manage... |
| consistent_with_playbook | yes | yes | True | The shelf is empty because there's a market-wide shortage, which means 9 units were cut from your delivery. Fill the ... |
| consistent_with_playbook | yes | yes | True | There's a market-wide shortage of Sour Cream 150ml, so your allocation was cut by 9 units. Fill the space with an app... |
| consistent_with_playbook | yes | yes | True | This line is being taken out of the range, so the gap is planned. No action is needed: don't chase the supplier or re... |
| consistent_with_playbook | no | no | True | Nothing has arrived, so place a second order for this line today to be safe. |
| consistent_with_playbook | no | no | True | The last delivery came in 6 units short, but there's nothing you need to do about it. |
| consistent_with_playbook | no | no | True | The shelf is empty, so chase the supplier today and reorder enough units to fill it. |
| consistent_with_playbook | no | no | True | There's a shortage, so raise a shortage query and chase Fernleigh Cheesemakers for the 9 missing units. |
| plain_english | yes | yes | True | The last delivery from Merseyvale DC came in 6 units short, so the shelf is empty. Raise a shortage query with the de... |
| plain_english | yes | yes | True | The shelf is empty because there's a market-wide shortage, which means 9 units were cut from your delivery. Fill the ... |
| plain_english | yes | yes | True | The system thought there were 4 units in store so it didn't order more, but they weren't actually here. Count the she... |
| plain_english | yes | yes | True | This sauce sold 4 units more than expected, so the shelf ran low even though it was stocked correctly. Order extra un... |
| plain_english | no | no | True | # Response for Shelf Scan Device  This sauce sold 4 units more than expected, so the shelf ran low. Order extra units... |
| plain_english | no | no | True | An inbound fulfilment non-conformance of 6 units has been identified against the ASN; initiate a supplier-short excep... |
| plain_english | no | no | True | Demand variance of 4 units against the statistical forecast has driven a sub-presentation-minimum inventory position;... |
| plain_english | no | no | True | STATUS: GAP. CAUSE: MARKET SHORTAGE. QTY CUT: 9. ACTION: SUBSTITUTE APPROVED ALTERNATIVE. END. |
| plain_english | no | no | True | Your stock file is wrong again. Count it properly this time and fix it. |

## Sample advice from the final run (two per root cause)

| root_cause | store | product | advice |
|---|---|---|---|
| INVESTIGATE | Beeston Local | Mayonnaise 400g Family Pack | The system hasn't found a reason yet for the gap on the Mayonnaise 400g Family Pack shelf. Please log this for the availability analyst to investigate so they can find out what's happened and get it sorted. |
| INVESTIGATE | Cumbernauld | Baking Powder 100g Multi-Buy | The shelf is empty for Baking Powder 100g Multi-Buy and we haven't found the reason yet in our systems. Please log this gap so the availability analyst can investigate what's causing it. |
| KNOWN_GAP | Hereford Local | Organic Carrots 500g | Organic Carrots 500g is leaving our range as planned, so the empty shelf is expected. No action is needed, as this product won't be restocked. |
| KNOWN_GAP | Lichfield Forecourt | Seeded Batch Loaf 400g Value Pack | The Seeded Batch Loaf 400g Value Pack is no longer part of our range and has been deliberately removed. This is a planned change, so no action is needed and there's nothing to chase or reorder. |
| ORDER_DELIVERY_BLOCK | Ashington | Plain Bagels 4pk Twin Pack | The order for Plain Bagels 4pk Twin Pack has been blocked or cancelled at Pennine DC, which is why there's nothing on the shelf. Contact Pennine DC to ask them to release the blocked order or speed it up, but don't place a second order. |
| ORDER_DELIVERY_BLOCK | Battersea Local | Unsalted Butter 500g Twin Pack | There's not enough stock on the shelf because an order for Unsalted Butter 500g Twin Pack has been blocked or cancelled, and it's selling faster than expected. Contact Riverside DC to release the blocked order or speed it up, but don't place a second order. |
| SCARCITY | Aviemore | Sour Cream 150ml 2 for £5 | There's a market-wide shortage of Sour Cream 150ml 2 for £5, so your allocation was cut by 9 units and nothing is available to send. Fill the space with an approved alternative line. |
| SCARCITY | Dalkeith High Street | Thyme 20g Family Pack | There's a market-wide shortage of Thyme 20g Family Pack, so your delivery was cut by 4 units and there's nothing left to sell. Fill the space with an approved alternative line. |
| STOCKFILE_ADJUSTMENT | Bridgwater Local | Digestives 800g Value Pack | The system thought there was stock when there wasn't, so it didn't order more. Count the shelf and stockroom now, then update the stock file so the system can start ordering Digestives 800g Value Pack again. |
| STOCKFILE_ADJUSTMENT | Harrow High Street | Vanilla Yogurt 4x125g Family Pack | The system thought there were 8 units in store so it didn't order more, but they weren't really there. Count the shelf and stockroom now, then correct the stock file so automatic ordering can restart. |
| SUPPLIER_SHORT | Grantham Local | Organic Fusilli 500g | The last delivery arrived 11 units short, which is why there's nothing on the shelf for Organic Fusilli 500g. Raise a shortage query with Midshire DC for the missing units and check when the next delivery is due. |
| SUPPLIER_SHORT | London Bridge Local | Organic Cheese & Pickle Sandwich 1pk | The last delivery arrived 11 units short, which is why there's nothing on the shelf. Raise a shortage query with Riverside DC for the missing units and check when the next delivery is due. |
| UNDER_FORECAST | Dalston Local | Kalamata Olives 320g Multi-Buy | The Kalamata Olives 320g Multi-Buy sold more than expected today, with 2 units sold above forecast, so the shelf is empty. Raise today's order and tell the ordering team the line is selling faster than forecast. |
| UNDER_FORECAST | Derby Station | Tuna Steaks 4pk 2 for £5 | The Tuna Steaks 4pk 2 for £5 sold 6 units more than expected, so the shelf is empty. Raise today's order and tell the ordering team the line is selling faster than forecast. |
| WASTE | Ashford Local | Soda Bread 400g 2 for £5 | The shelf is empty because 2 units were written off as waste. Check the date codes and how the product is being handled, then ask for the order quantity on this short-life line to be reviewed. |
| WASTE | Barbican Local | Organic Prosciutto 140g | Stock is low because 4 units were written off as waste, leaving only 1 unit on a shelf that needs at least 3 units. Check the date codes and handling of this short-life product, then ask for the order quantity to be reviewed. |
