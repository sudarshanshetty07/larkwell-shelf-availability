"""Next best action for a Shelf Scan: the prompt, the playbook and a deterministic fallback.

Shared by the app (/api/sst-explain) and the offline evaluation (genai/03_evaluate_next_best_action), so the
evaluation tests exactly what store colleagues see.

The model never works anything out for itself. The root cause comes from the pipeline's rules, every number is
passed in as plain text, and the recommended action comes from the playbook below. The model's only job is to say
it clearly for a colleague standing at the shelf.
"""
import re

PROMPT_VERSION = "nba-v4"

REASON_LABEL = {
    "KNOWN_GAP": "a planned range exit, so the gap is deliberate",
    "SCARCITY": "a market-wide shortage that cut this store's allocation",
    "SUPPLIER_SHORT": "the last delivery arrived short",
    "ORDER_DELIVERY_BLOCK": "an order for this line is blocked or was cancelled",
    "STOCKFILE_ADJUSTMENT": "phantom stock: the system believed there was stock, so it didn't reorder",
    "WASTE": "stock was written off as waste",
    "UNDER_FORECAST": "it sold more than its forecast",
    "INVESTIGATE": "no cause has been found in the data yet",
}

ACTION_BY_REASON = {
    "KNOWN_GAP": "No action needed: this is a planned range exit. Don't chase the supplier and don't reorder.",
    "SCARCITY": "No supplier chase is needed because the shortage is market-wide. Fill the space with an approved alternative line.",
    "SUPPLIER_SHORT": "Raise a shortage query with the depot for the missing units and check when the next delivery is due.",
    "ORDER_DELIVERY_BLOCK": "Ask the depot to release the blocked order or speed it up. Don't place a second order.",
    "STOCKFILE_ADJUSTMENT": "Count the shelf and the stockroom, then correct the stock file so automatic ordering restarts.",
    "WASTE": "Check date codes and handling, and ask for the order quantity on this short-life line to be reviewed.",
    "UNDER_FORECAST": "Raise today's order and tell the ordering team the line is selling faster than forecast. It isn't a store mistake.",
    "INVESTIGATE": "Log it for the availability analyst to investigate. Don't guess the cause.",
}

# The evidence for each root cause, as a sentence with the quantity filled in.
EVIDENCE = {
    "SUPPLIER_SHORT": ("supplier_short_qty", "{u} short on the last delivery"),
    "SCARCITY": ("scarcity_qty", "{u} cut from the allocation"),
    "WASTE": ("waste_qty", "{u} written off as waste"),
    "UNDER_FORECAST": ("under_forecast_qty", "{u} sold above forecast"),
    "STOCKFILE_ADJUSTMENT": ("stockfile_adjustment_qty", "the last count found {u} of phantom stock"),
}

STATUS_LABEL = {"GAP": "Gap: nothing on the shelf", "LOW": "Low: below the shelf's minimum display"}
LOW_LABEL = {"SALES_LOW": "it is selling faster than planned", "SPACE_LOW": "the shelf can't hold a day's demand"}

SYSTEM_PROMPT = (
    "You help Larkwell Foods store colleagues act on an empty or low shelf. They read your answer on a handheld "
    "Shelf Scan device, standing at the shelf.\n"
    "Write 2 or 3 short sentences in plain British English: first what is wrong and why, in everyday words, then the "
    "one thing the colleague should do now.\n"
    "Rules:\n"
    "- Follow the recommended action. Never contradict it: for example, never ask anyone to chase a supplier for a "
    "planned range exit or a market-wide shortage.\n"
    "- Use numbers exactly as they are written in the facts. Don't round, estimate or work out new numbers.\n"
    "- The only unit is \"units\". Never mention cases, packs, boxes or weights unless they are part of the product name.\n"
    "- Only say what the facts say. Don't guess at extra causes or outcomes, such as why stock was wasted or whether a "
    "line will come back.\n"
    "- Reply with the sentences only: no title, heading, bullet points or bold text.\n"
    "- Don't use internal codes such as SUPPLIER_SHORT, and don't mention confidence scores or data sources."
)


def _units(value):
    try:
        return int(round(float(value or 0)))
    except (TypeError, ValueError):
        return 0


def _u(n):
    return f"{n} unit" if n == 1 else f"{n} units"


def facts(event, store):
    """The facts the model may use, written out in plain English."""
    reason = event.get("consensus_reason") or "INVESTIGATE"
    issue = event.get("issue") or "GAP"
    status = STATUS_LABEL.get(issue, issue)
    if issue == "LOW" and event.get("low_issue") in LOW_LABEL:
        status += f", because {LOW_LABEL[event['low_issue']]}"
    lines = [f"Product: {event.get('product', 'this line')}", f"Store: {store}", f"Shelf status: {status}",
             f"Root cause: {REASON_LABEL.get(reason, REASON_LABEL['INVESTIGATE'])}"]
    if reason in EVIDENCE:
        col, template = EVIDENCE[reason]
        n = _units(event.get(col))
        if n > 0:
            lines.append("Evidence: " + template.format(u=_u(n)))
    if issue == "LOW" and event.get("on_hand_units") is not None:
        lines.append(f"On the shelf now: {_u(_units(event.get('on_hand_units')))} "
                     f"(minimum display {_u(_units(event.get('presentation_min_units')))})")
    if reason in ("SUPPLIER_SHORT", "SCARCITY") and event.get("supplier"):
        lines.append(f"Supplier: {event['supplier']}")
    if reason in ("SUPPLIER_SHORT", "ORDER_DELIVERY_BLOCK") and event.get("depot"):
        lines.append(f"Depot: {event['depot']}")
    lines.append(f"Recommended action: {ACTION_BY_REASON.get(reason, ACTION_BY_REASON['INVESTIGATE'])}")
    return "\n".join(lines)


_MARKUP = [
    (re.compile(r"^\s{0,3}#{1,6}\s.*$", re.M), ""),      # a heading line, e.g. "# Response for Shelf Scan Device"
    (re.compile(r"^\s*(?:[-*•]|\d+\.)\s+", re.M), ""),   # bullet or numbered-list markers
    (re.compile(r"(\*\*|__)(.+?)\1"), r"\2"),             # bold
]


def clean(text):
    """What the colleague sees: the model's words as plain sentences. The prompt forbids headings and markup, but the
    model occasionally adds a title anyway (2 of 48 cases in one evaluation), so they're removed before display."""
    for pattern, repl in _MARKUP:
        text = pattern.sub(repl, text or "")
    return " ".join(text.split())


def build_messages(event, store):
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Facts:\n" + facts(event, store)}]


def allowed_numbers(event, store):
    """Every number the model is allowed to say: the ones in the facts (including product names like 400g)."""
    return set(re.findall(r"\d+(?:\.\d+)?", facts(event, store)))


def fallback(event, store):
    """Used if the model is unavailable: the same facts as a fixed sentence, so the colleague always gets an answer."""
    reason = event.get("consensus_reason") or "INVESTIGATE"
    issue = STATUS_LABEL.get(event.get("issue") or "GAP", "Gap").split(":")[0]
    return f"{issue} because {REASON_LABEL.get(reason, REASON_LABEL['INVESTIGATE'])}. {ACTION_BY_REASON.get(reason, ACTION_BY_REASON['INVESTIGATE'])}"
