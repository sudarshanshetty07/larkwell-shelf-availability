"""Shared definitions for the gap-risk model: its features, the rules it has to beat, how it's measured, and the
plain-English reasons shown with each prediction. Used by ml/01_train_gap_risk.py and ml/02_score_gap_risk.py.

The model predicts, the day before, which product-locations will be empty the next morning for an unplanned reason
(anything except a planned range exit). Every input comes from ml.gap_risk_features, which the Lakeflow pipeline builds.
"""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

FEATURES = [
    "is_gap", "is_low", "on_hand", "presentation_min", "shelf_capacity", "forecast", "sales", "days_of_cover",
    "fill_ratio", "sold_over_forecast", "short_units", "open_blocks", "phantom_units", "waste_units", "shortage_units",
    "gap_days_7d", "exception_days_7d", "short_days_7d", "block_days_7d", "gap_yesterday", "store_gap_rate_today",
    "store_gap_rate_7d", "line_gap_rate_today", "line_gap_rate_7d", "line_shortage_rate_today",
    "supplier_short_rate_today", "supplier_short_rate_3d", "depot_block_rate_today", "depot_block_rate_3d",
    "depot_short_rate_today", "target_dow", "shelf_life_days", "unit_price_gbp", "on_promotion",
]
LIST_SIZE = 25          # a store's watch list: the lines it checks before close

# The rules the model has to beat. Both use only what a store already sees in this morning's report.
RULES = {
    "today_rule": "What's empty or low this morning, least stock first",
    "lowest_cover_rule": "Lowest stock against forecast first",
}


def rule_scores(df):
    """Scores for the two rules (higher means more likely to be empty tomorrow)."""
    cover = df.days_of_cover.clip(upper=10)
    return {"today_rule": df.is_gap + 0.5 * df.is_low + 0.01 * (1 - cover / 10), "lowest_cover_rule": -df.days_of_cover}


def list_hits(day, score, n=LIST_SIZE):
    """For one day: how many lines on each store's top-n list by `score` were empty the next morning."""
    top = day.assign(_s=score).sort_values("_s", ascending=False, kind="stable").groupby("store_id", sort=False).head(n)
    return int(top.label.sum()), len(top)


def summarise(y, scores, hits, total_positives):
    """AUC, average precision and watch-list precision and capture for each scorer. `hits[name] = (hits, listed)`."""
    out = {}
    for name, s in scores.items():
        h, listed = hits[name]
        out[name] = {"auc": float(roc_auc_score(y, s)), "average_precision": float(average_precision_score(y, s)),
                     "list_precision": h / listed if listed else 0.0,
                     "list_capture": h / total_positives if total_positives else 0.0}
    return out


# Plain-English reasons. Each feature's contribution is attributed to one of these, and the strongest three are shown. A
# reason is used only when the line's own value makes the sentence true (a contribution can be positive even when, say,
# the line wasn't empty yesterday), and thresholds sit well above the typical value so "more than most" is a fact.
def _n(v):
    return int(round(float(v)))


REASONS = {  # feature -> (when the sentence is true, the sentence)
    "is_gap": (lambda r: r.is_gap == 1, lambda r: "Empty this morning"),
    "gap_yesterday": (lambda r: r.gap_yesterday == 1,
                      lambda r: "Empty yesterday too" if r.is_gap == 1 else "Empty yesterday, refilled today"),
    "gap_days_7d": (lambda r: r.gap_days_7d >= 2, lambda r: f"Empty on {_n(r.gap_days_7d)} of the last 7 days"),
    "exception_days_7d": (lambda r: r.exception_days_7d >= 2,      # when every one of those days was empty, say so
                          lambda r: (f"Empty on {_n(r.gap_days_7d)} of the last 7 days" if r.gap_days_7d == r.exception_days_7d
                                     else f"Empty or low on {_n(r.exception_days_7d)} of the last 7 days")),
    "is_low": (lambda r: r.is_low == 1, lambda r: f"Low: {_n(r.on_hand)} on a shelf that should show {_n(r.presentation_min)}"),
    "days_of_cover": (lambda r: r.is_gap == 0 and r.days_of_cover < 1,
                      lambda r: f"Only {float(r.days_of_cover):.1f} days of stock at the forecast"),
    "fill_ratio": (lambda r: r.is_gap == 0 and r.fill_ratio < 0.4, lambda r: f"Shelf only {float(r.fill_ratio):.0%} full"),
    "on_hand": (lambda r: r.is_gap == 0 and r.on_hand <= 3, lambda r: f"Only {_n(r.on_hand)} left on the shelf"),
    "short_units": (lambda r: r.short_units > 0, lambda r: f"Today's delivery came {_n(r.short_units)} short"),
    "short_days_7d": (lambda r: r.short_days_7d >= 2, lambda r: f"Short deliveries on {_n(r.short_days_7d)} of the last 7 days"),
    "open_blocks": (lambda r: r.open_blocks > 0, lambda r: "An order is blocked at the depot"),
    "block_days_7d": (lambda r: r.block_days_7d >= 2, lambda r: f"Orders blocked on {_n(r.block_days_7d)} of the last 7 days"),
    "phantom_units": (lambda r: r.phantom_units > 0,
                      lambda r: (f"A stock count found {_n(r.phantom_units)} units that weren't there" if _n(r.phantom_units) != 1
                                 else "A stock count found 1 unit that wasn't there")),
    "waste_units": (lambda r: r.waste_units > 0, lambda r: f"{_n(r.waste_units)} written off as waste today"),
    "shortage_units": (lambda r: r.shortage_units > 0, lambda r: f"Allocation cut by {_n(r.shortage_units)} in a market shortage"),
    "line_shortage_rate_today": (lambda r: r.line_shortage_rate_today >= 0.1,
                                 lambda r: f"Market shortage: allocation cut in {float(r.line_shortage_rate_today):.0%} of stores"),
    "line_gap_rate_today": (lambda r: r.line_gap_rate_today >= 0.04,
                            lambda r: f"Empty in {float(r.line_gap_rate_today):.0%} of stores today"),
    "line_gap_rate_7d": (lambda r: r.line_gap_rate_7d >= 0.04,
                         lambda r: f"Often empty across stores ({float(r.line_gap_rate_7d):.0%} this week)"),
    "supplier_short_rate_today": (lambda r: r.supplier_short_rate_today >= 0.3,
                                  lambda r: f"Supplier short on {float(r.supplier_short_rate_today):.0%} of lines today"),
    "supplier_short_rate_3d": (lambda r: r.supplier_short_rate_3d >= 0.3,
                               lambda r: f"Supplier short on {float(r.supplier_short_rate_3d):.0%} of lines lately"),
    "depot_block_rate_today": (lambda r: r.depot_block_rate_today >= 0.012, lambda r: "Its depot is blocking more orders than most"),
    "depot_block_rate_3d": (lambda r: r.depot_block_rate_3d >= 0.012, lambda r: "Its depot is blocking more orders than most"),
    "depot_short_rate_today": (lambda r: r.depot_short_rate_today >= 0.23, lambda r: "Its depot's deliveries are running short"),
    "store_gap_rate_today": (lambda r: r.store_gap_rate_today >= 0.025,
                             lambda r: f"Store has more empty shelves than most today ({float(r.store_gap_rate_today):.1%})"),
    "store_gap_rate_7d": (lambda r: r.store_gap_rate_7d >= 0.025, lambda r: "Store has had more empty shelves than most this week"),
    "sold_over_forecast": (lambda r: r.sold_over_forecast > 0, lambda r: "Selling faster than forecast"),
    "sales": (lambda r: r.sales > r.forecast, lambda r: "Selling faster than forecast"),
    "forecast": (lambda r: False, lambda r: None),
    "target_dow": (lambda r: r.target_dow in (0, 5, 6), lambda r: "Tomorrow is one of the week's busiest days"),
    "on_promotion": (lambda r: r.on_promotion == 1, lambda r: "On promotion"),
    "shelf_life_days": (lambda r: r.shelf_life_days <= 3,
                        lambda r: f"Short shelf life ({_n(r.shelf_life_days)} day{'' if _n(r.shelf_life_days) == 1 else 's'})"),
    "presentation_min": (lambda r: False, lambda r: None),
    "shelf_capacity": (lambda r: r.shelf_capacity < 2 * r.forecast, lambda r: "Small shelf for how fast it sells"),
    "unit_price_gbp": (lambda r: False, lambda r: None),
}


def top_reasons(contributions, rows, k=3):
    """The k strongest reasons pushing each row's risk up, from LightGBM's per-feature contributions (SHAP values).
    `contributions` has one column per feature plus the bias in the last column, and lines up with `rows`."""
    out = []
    contrib = contributions[:, :len(FEATURES)]
    for i, r in enumerate(rows.itertuples(index=False)):
        texts = []
        for j in np.argsort(-contrib[i]):
            if contrib[i, j] <= 0 or len(texts) == k:
                break
            true_for_line, sentence = REASONS[FEATURES[j]]
            t = sentence(r) if true_for_line(r) else None
            if t and t not in texts:
                texts.append(t)
        out.append(texts + [None] * (k - len(texts)))
    return pd.DataFrame(out, columns=[f"reason_{i + 1}" for i in range(k)], index=rows.index)
