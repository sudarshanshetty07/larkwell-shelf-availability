# Value model

Larkwell Foods is fictitious and its data is synthetic, calibrated to the scale of a large UK food retailer.
Each number below is labelled with its source:
- **DATA** comes from this build (gold table and metric view, business date 2026-10-19; the queries are in `evidence/`);
- **PUBLIC** comes from published research;
- **ASSUMPTION** is an estimate to validate with the customer in a pilot.

## The base: what's at risk today

| Measure | Value | Source |
|---|---|---|
| Stores x lines (product-locations) | 900 x 6,000 = 5.4M | DATA |
| Forecast demand per day | £22.6m (about £8.2bn a year) | DATA: sum of forecast units x price |
| On-shelf availability | 97.52% (gap rate 2.48%) | DATA: metric view |
| Gaps and lows each morning | 205,834 (229 per store) | DATA |
| Sales at risk on gaps and lows | £1.55m a day: demand not covered by stock on hand | DATA: `est_sales_at_risk_gbp` |
| ...of which planned range exits (no action needed) | £0.37m a day | DATA |
| ...of which market-wide scarcity (substitute only) | £0.09m a day | DATA |
| **Controllable sales at risk** | **£1.09m a day across 127,010 gaps and lows** | DATA |
| Share of at-risk demand actually lost to the retailer | 40%: 31% of shoppers buy elsewhere and 9% don't buy; the rest substitute or delay | PUBLIC: Gruen, Corsten and Bharadwaj, *Retail Out-of-Stocks: A Worldwide Examination of Extent, Causes and Consumer Responses* (GMA/FMI/CIES, 2002) |
| **Controllable lost sales** | **£0.43m a day, about £158m a year (1.9% of sales)** | DATA x PUBLIC |

The same study found most out-of-stocks start with store ordering, forecasting and replenishment practices. That's why the
controllable share is large, and why a store colleague needs the cause, not just the gap.

## Value lever 1: sales recovered (executive sponsor, COO)

Every morning the root cause and the next action reach a colleague's handheld. Each action they log comes back to head office within a minute. The lever is the share of controllable lost sales that faster, targeted action prevents.

| Scenario | Share of controllable lost sales prevented | Sales recovered a year | Source |
|---|---|---|---|
| Conservative | 10% | **£15.8m** | ASSUMPTION |
| Base | 15% | **£23.7m** | ASSUMPTION |
| Stretch | 25% | **£39.5m** | ASSUMPTION |

These are sales, not profit. At an assumed 25% gross margin (ASSUMPTION; typical for UK food retail), the base case is about **£5.9m of gross profit a year** (£4.0m-£9.9m).

The availability gain implied by the base case is about +0.2 percentage points: 15% of the 82,502 controllable gaps, over
5.4M product-locations. The pilot measures this directly: repeat gaps and time from snapshot to action, in pilot stores against control stores.

## Value lever 2: store time given back (domain owner, Head of Availability; and store operations)

| Input | Value | Source |
|---|---|---|
| Manual "why is this empty?" checks per store per day today | 20 | ASSUMPTION |
| Minutes saved per check (Shelf Scan answers in milliseconds, with the action) | 3 | ASSUMPTION |
| Hours given back per day across 900 stores | 900 | Calculated |
| Loaded colleague cost per hour | £13 | ASSUMPTION |
| **Value a year** | **about £4.3m** (about 328,000 hours) | Calculated |

This is capacity given back to stores for replenishment and customers, not a headcount saving.

## Value lever 3: decisions head office can now make (domain owner)

| Insight surfaced by the build | Value | Source |
|---|---|---|
| Gaps and lows with a confirmed root cause | 98.0% (only 4,085 left for an analyst) | DATA |
| Worst supplier: Oldcastle Confectionery | 59.1% fill rate against a 99.0% contract; 50,741 units short in a day | DATA |
| Worst depot for blocked orders: Merseyvale DC | 6,078 blocked product-locations across 130 stores | DATA |
| Biggest controllable cause by sales at risk | Under-forecast: £0.52m a day across 30,989 lines | DATA |

These turn into supplier service-level conversations, a depot fix and forecast tuning. I don't put a single figure on them here.

## Cost to run (indicative)

| Component | Assumption | Estimate a year |
|---|---|---|
| Lakeflow pipeline and daily job | Serverless, about 10 minutes a day | Low thousands of pounds |
| Lakebase | Autoscaling 1-8 CU, about 2 CU on average | Under £10k |
| Databricks App | One medium app, always on | Under £10k |
| SQL warehouse for dashboards and Genie | Shared serverless warehouse, business hours | £10k-£20k |
| LLM next best action | About 36,000 calls a day; a smaller model or caching cuts this several-fold | £10k-£40k |
| **Total** | | **roughly £40k-£90k a year** |

Costs are indicative, based on list prices; confirm them with the account team. Even at the top of the range, the base case returns more
than 200 times its run cost in sales, and more than 60 times in gross profit.

## How the pilot proves it

- **Design:** 20 pilot stores against 20 matched control stores, for 6 weeks.
- **Measure:** controllable gap rate, repeat gaps, time from morning snapshot to logged action, the share of exceptions with an action, and colleague minutes per check.
- **Data:** everything needed is already in `gold.product_location_status`, `gold.colleague_actions` and `gold.shelf_scans`.
