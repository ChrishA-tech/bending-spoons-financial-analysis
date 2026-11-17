"""Compute the metrics that answer five questions about Bending Spoons' numbers.

1. How much growth is bought vs organic?   2. How profitable is it (GAAP vs adjusted)?
3. Does profit turn into cash?             4. Can it carry its acquisition debt?   5. Is the guidance consistent?

Every metric is computed from data/financials.csv; nothing is typed in by hand.
"""
import json
import re
from typing import Dict, List, Optional

import pandas as pd

from . import config as C

QUARTER = re.compile(r"^Q[1-4] \d{4}$")


class Book:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get(self, patterns: List[str], period: str, statements: List[str] = None, unit: str = "usd_thousands") -> Optional[float]:
        """First matching figure: line items matched case-insensitively (exact, then 'starts with')."""
        d = self.df[(self.df.period == period) & (self.df.unit == unit)]
        if statements:
            d = d[d.statement.isin(statements)]
        for p in patterns:
            for mode in ("exact", "start"):
                li = d.line_item.str.lower()
                m = d[li == p.lower()] if mode == "exact" else d[li.str.startswith(p.lower())]
                if len(m):
                    return float(m.value.iloc[0])
        return None

    def periods(self, kind: str) -> List[str]:
        ps = sorted(set(self.df.period), key=_period_key)
        if kind == "quarter":
            return [p for p in ps if QUARTER.match(p)]
        if kind == "ytd":
            return [p for p in ps if p.split()[0] in ("H1", "9M", "FY")]
        return [p for p in ps if re.match(r"\d{4}-\d{2}-\d{2}$", p)]


def _period_key(p: str):
    if re.match(r"\d{4}-\d{2}-\d{2}$", p):
        return (p[:4], p)
    tag, year = (p.split() + [""])[:2]
    return (year, {"Q1": "1", "Q2": "2", "H1": "2h", "Q3": "3", "9M": "3m", "Q4": "4", "FY": "4y"}.get(tag, tag))


def _pct(a, b):
    return None if a is None or b in (None, 0) else round(100 * a / b, 1)


def _growth(a, b):
    return None if a is None or b in (None, 0) else round(100 * (a / b - 1), 1)


REV = ["Revenue"]
IS = ["income_statement", "operating_results"]


def quarterly(b: Book, facts: Dict) -> pd.DataFrame:
    rows = []
    qs = set(b.periods("quarter"))
    # Q1 = H1 - Q2 when only the half-year is reported
    for p in b.periods("ytd"):
        if p.startswith("H1 "):
            y = p.split()[1]
            if f"Q1 {y}" not in qs and f"Q2 {y}" in qs:
                qs.add(f"Q1 {y}")
    for q in sorted(qs, key=_period_key):
        y = q.split()[1]
        def g(pats, sts=IS, period=q):
            v = b.get(pats, period, sts)
            if v is None and q.startswith("Q1 ") and period == q:      # derive Q1 from H1 - Q2
                h1, q2 = b.get(pats, f"H1 {y}", sts), b.get(pats, f"Q2 {y}", sts)
                v = None if h1 is None or q2 is None else h1 - q2
            return v
        rev, gp, oi = g(REV), g(["Gross profit"]), g(["Operating income"])
        ni = g(["Net income (loss)", "Net income"])
        aoi = g(["Adjusted Operating Income"], ["adjusted_measures", "recon_operating_income"])
        interest = g(["Interest expense"], ["income_statement"])
        prev = f"{q.split()[0]} {int(y) - 1}"
        rev_prev = b.get(REV, prev, IS)
        if rev_prev is None and q.startswith("Q1 "):
            h1, q2 = b.get(REV, f"H1 {int(y) - 1}", IS), b.get(REV, f"Q2 {int(y) - 1}", IS)
            rev_prev = None if h1 is None or q2 is None else h1 - q2
        amort = g(["Amortization and impairment of acquired intangible assets"], ["recon_operating_income"])
        reorg = g(["Reorganization-related expense"], ["recon_operating_income"])
        trans = g(["Transaction-related expense"], ["recon_operating_income"])
        org = (facts.get(q) or {}).get("organic_growth_pct")
        rows.append({
            "period": q, "revenue_m": _m(rev), "revenue_growth_yoy_pct": _growth(rev, rev_prev),
            "organic_growth_pct": org,
            "acquired_growth_pct": None if org is None or _growth(rev, rev_prev) is None else round(_growth(rev, rev_prev) - org, 1),
            "gross_margin_pct": _pct(gp, rev), "operating_margin_pct": _pct(oi, rev),
            "adj_operating_margin_pct": _pct(aoi, rev), "net_margin_pct": _pct(ni, rev),
            "gap_adj_vs_gaap_pp": None if aoi is None or oi is None or not rev else round(100 * (aoi - oi) / rev, 1),
            "amortisation_pct_rev": _pct(amort, rev), "reorganisation_pct_rev": _pct(reorg, rev),
            "transaction_pct_rev": _pct(trans, rev),
            "interest_coverage_x": None if oi is None or not interest else round(oi / interest, 2),
            "operating_income_m": _m(oi), "adj_operating_income_m": _m(aoi), "net_income_m": _m(ni),
            "interest_expense_m": _m(interest),
        })
    return pd.DataFrame(rows)


def cash(b: Book) -> pd.DataFrame:
    rows = []
    for p in b.periods("ytd"):
        cf = ["cash_flow"]
        ocf = b.get(["Net cash from operating activities"], p, cf)
        if ocf is None:
            continue
        capex = sum(v for v in (b.get(["Purchase of property, plant, and equipment"], p, cf),
                                b.get(["Purchase of intangible assets"], p, cf)) if v is not None)
        ni = b.get(["Net income (loss)", "Net income"], p, cf)
        rev = b.get(REV, p, IS)
        acq = b.get(["Acquisitions of businesses"], p, cf)
        fcf = ocf + capex                                   # capex is negative in the cash flow statement
        rows.append({"period": p, "operating_cash_flow_m": _m(ocf), "capex_m": _m(capex), "free_cash_flow_m": _m(fcf),
                     "fcf_margin_pct": _pct(fcf, rev), "cash_conversion_ocf_to_net_income": None if not ni or ni <= 0 else round(ocf / ni, 2),
                     "acquisitions_m": _m(acq), "acquisitions_to_fcf_x": None if acq is None or fcf <= 0 else round(-acq / fcf, 1),
                     "debt_raised_m": _m(b.get(["Proceeds from issuance of debt"], p, cf)),
                     "interest_paid_m": _m(b.get(["Interests paid", "Interest paid"], p, cf))})
    return pd.DataFrame(rows)


def balance(b: Book, q: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d in b.periods("date"):
        bs = ["balance_sheet"]
        get = lambda pats: b.get(pats, d, bs)                                   # noqa: E731
        cash_ = get(["Cash and cash equivalents"])
        debt = sum(v for v in (get(["Long-term debt, current"]), get(["Long-term debt, non-current"])) if v is not None) or None
        gw = sum(v for v in (get(["Goodwill"]), get(["Intangible assets, net"])) if v is not None) or None
        assets, equity = get(["Total assets"]), get(["Total shareholders' equity", "Total shareholders’ equity", "Total equity"])
        defrev = sum(v for v in (get(["Deferred revenue, current"]), get(["Deferred revenue, non-current"])) if v is not None) or None
        qlabel = {"03-31": "Q1", "06-30": "Q2", "09-30": "Q3", "12-31": "Q4"}[d[5:]] + " " + d[:4]
        aoi_row = q[q.period == qlabel]
        aoi = aoi_row.adj_operating_income_m.iloc[0] if len(aoi_row) else None
        net_debt = None if debt is None or cash_ is None else debt - cash_
        rows.append({"date": d, "cash_m": _m(cash_), "total_debt_m": _m(debt), "net_debt_m": _m(net_debt),
                     "goodwill_intangibles_pct_assets": _pct(gw, assets), "equity_m": _m(equity),
                     "debt_to_equity_x": None if not equity or debt is None else round(debt / equity, 2),
                     "deferred_revenue_m": _m(defrev),
                     "net_debt_to_annualised_adj_op_income_x": None if aoi in (None, 0) or net_debt is None or pd.isna(aoi)
                     else round(net_debt / 1000 / (4 * aoi), 2)})
    return pd.DataFrame(rows)


def guidance(facts: Dict) -> List[Dict]:
    out = [{"release": rel, **g} for rel, f in facts.items() for g in f.get("guidance_ranges", [])]
    if out:
        return out
    for rel, f in facts.items():
        for s in f.get("guidance", []):
            m = re.search(r"(Q[1-4] \d{4}|fiscal \d{4}|full[- ]year \d{4}|\d{4})[^$]*?revenue[^$]*\$([\d.,]+)\s*(million|billion)\s*(?:and|to|-|–)\s*\$([\d.,]+)\s*(million|billion)", s, re.I)
            if not m:
                continue
            k = lambda v, u: float(v.replace(",", "")) * (1000 if u.lower() == "billion" else 1)   # noqa: E731
            lo, hi = k(m.group(2), m.group(3)), k(m.group(4), m.group(5))
            out.append({"release": rel, "target": m.group(1), "revenue_low_m": lo, "revenue_high_m": hi,
                        "midpoint_m": round((lo + hi) / 2, 1), "sentence": s})
    return out


def _m(v):
    return None if v is None else round(v / 1000, 1)


def run(df: pd.DataFrame = None) -> Dict:
    df = pd.read_csv(C.DATA / "financials.csv") if df is None else df
    facts = json.loads((C.DATA / "text_facts.json").read_text())
    b = Book(df)
    q, c = quarterly(b, facts), cash(b)
    bs, g = balance(b, q), guidance(facts)
    C.OUT.mkdir(parents=True, exist_ok=True)
    q.to_csv(C.OUT / "quarterly_metrics.csv", index=False)
    c.to_csv(C.OUT / "cash_metrics.csv", index=False)
    bs.to_csv(C.OUT / "balance_metrics.csv", index=False)
    (C.OUT / "guidance.json").write_text(json.dumps(g, indent=2))
    return {"quarterly": q, "cash": c, "balance": bs, "guidance": g, "facts": facts}
