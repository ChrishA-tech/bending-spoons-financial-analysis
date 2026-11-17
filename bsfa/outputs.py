"""Excel workbook, charts and a findings sheet from the computed metrics."""
import json
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.chart import BarChart, LineChart, Reference  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

from . import config as C  # noqa: E402

INK, ACCENT, MUTED = "#1f2937", "#0f766e", "#9ca3af"


def _sheet(wb, title, df: pd.DataFrame, note: str = ""):
    ws = wb.create_sheet(title)
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True)
        r0 = 3
    for j, col in enumerate(df.columns, 1):
        c = ws.cell(r0, j, col)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F2937")
        ws.column_dimensions[get_column_letter(j)].width = max(12, min(48, len(str(col)) + 2))
    for i, row in enumerate(df.itertuples(index=False), r0 + 1):
        for j, v in enumerate(row, 1):
            cell = ws.cell(i, j, None if pd.isna(v) else v)
            if df.columns[j - 1] == "source_url" and isinstance(v, str):
                cell.hyperlink, cell.font = v, Font(color="0563C1", underline="single")
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws, r0


def excel(df: pd.DataFrame, r: Dict, path=None):
    path = path or C.OUT / "bending_spoons_analysis.xlsx"
    wb = Workbook()
    wb.remove(wb.active)
    q = r["quarterly"]
    ws, r0 = _sheet(wb, "Quarterly", q, "USD millions unless stated. Every input is in the 'Figures' sheet with a link "
                                       "to the SEC filing it came from.")
    n = len(q)
    if n:
        bar = BarChart()
        bar.title, bar.y_axis.title = "Revenue by quarter (USD m)", "USD m"
        bar.add_data(Reference(ws, min_col=2, min_row=r0, max_row=r0 + n), titles_from_data=True)
        bar.set_categories(Reference(ws, min_col=1, min_row=r0 + 1, max_row=r0 + n))
        ws.add_chart(bar, f"A{r0 + n + 3}")
        line = LineChart()
        line.title, line.y_axis.title = "Margins (%)", "%"
        for name in ("operating_margin_pct", "adj_operating_margin_pct", "net_margin_pct"):
            col = list(q.columns).index(name) + 1
            line.add_data(Reference(ws, min_col=col, min_row=r0, max_row=r0 + n), titles_from_data=True)
        line.set_categories(Reference(ws, min_col=1, min_row=r0 + 1, max_row=r0 + n))
        ws.add_chart(line, f"J{r0 + n + 3}")
    _sheet(wb, "Cash flow", r["cash"], "Year-to-date periods (H1 = six months, 9M = nine months). Capex is negative "
                                       "(cash out); free cash flow = operating cash flow + capex.")
    _sheet(wb, "Balance sheet", r["balance"], "Net debt = long-term debt (current + non-current) - cash. Leverage uses "
                                              "annualised adjusted operating income as a proxy (the company reports "
                                              "leverage on its own adjusted EBITDA definition).")
    _sheet(wb, "Guidance", pd.DataFrame(r["guidance"]), "Revenue guidance as stated in each release.")
    _sheet(wb, "Figures", df, "Every figure extracted from the releases, with its source filing.")
    wb.save(path)
    return path


def charts(r: Dict):
    q = r["quarterly"].dropna(subset=["revenue_m"])
    out = []
    if len(q):
        fig, ax = plt.subplots(figsize=(7, 3.6))
        ax.bar(q.period, q.revenue_m, color=ACCENT)
        for x, v in zip(q.period, q.revenue_m):
            ax.text(x, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_title("Revenue by quarter (USD m)", loc="left", fontsize=11, color=INK)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); p = C.OUT / "revenue.png"; fig.savefig(p, dpi=160); plt.close(fig); out.append(p)

        g = q.dropna(subset=["revenue_growth_yoy_pct"])
        if len(g):
            fig, ax = plt.subplots(figsize=(7, 3.6))
            known = g.organic_growth_pct.notna()
            org = g.organic_growth_pct.where(known, 0)
            ax.bar(g.period[known], org[known], color=INK, label="Organic growth")
            ax.bar(g.period[known], (g.revenue_growth_yoy_pct - org)[known], bottom=org[known], color=MUTED,
                   label="From acquisitions")
            if (~known).any():
                ax.bar(g.period[~known], g.revenue_growth_yoy_pct[~known], color="white", edgecolor=MUTED, hatch="///",
                       label="Split not stated in this release")
            for x, t, o in zip(g.period, g.revenue_growth_yoy_pct, g.organic_growth_pct):
                ax.text(x, t, f"{t:.0f}%" + ("" if pd.isna(o) else f"\n(organic {o:.0f}%)"), ha="center", va="bottom", fontsize=8)
            ax.set_title("Revenue growth vs same quarter last year: organic vs acquired", loc="left", fontsize=11, color=INK)
            ax.legend(frameon=False, fontsize=8); ax.spines[["top", "right"]].set_visible(False)
            ax.set_ylim(0, g.revenue_growth_yoy_pct.max() * 1.3)
            fig.tight_layout(); p = C.OUT / "growth_organic_vs_acquired.png"; fig.savefig(p, dpi=160); plt.close(fig); out.append(p)

        m = q.dropna(subset=["operating_margin_pct"])
        fig, ax = plt.subplots(figsize=(7, 3.6))
        for col, lab, colr in (("adj_operating_margin_pct", "Adjusted operating margin", ACCENT),
                               ("operating_margin_pct", "Operating margin (IFRS)", INK),
                               ("net_margin_pct", "Net margin", MUTED)):
            s = m[["period", col]].dropna()
            ax.plot(s.period, s[col], marker="o", color=colr, label=lab)
        ax.axhline(0, color=MUTED, lw=0.6)
        ax.set_title("Margins (% of revenue)", loc="left", fontsize=11, color=INK)
        ax.legend(frameon=False, fontsize=8); ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); p = C.OUT / "margins.png"; fig.savefig(p, dpi=160); plt.close(fig); out.append(p)

    c = r["cash"]
    if len(c):
        fig, ax = plt.subplots(figsize=(7, 3.6))
        x = range(len(c))
        ax.bar([i - 0.2 for i in x], c.free_cash_flow_m, width=0.4, color=ACCENT, label="Free cash flow")
        ax.bar([i + 0.2 for i in x], -c.acquisitions_m.fillna(0), width=0.4, color=INK, label="Spent on acquisitions")
        ax.set_xticks(list(x), c.period)
        ax.set_title("Cash generated vs cash spent on acquisitions (USD m, year to date)", loc="left", fontsize=11, color=INK)
        ax.legend(frameon=False, fontsize=8); ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout(); p = C.OUT / "cash_vs_acquisitions.png"; fig.savefig(p, dpi=160); plt.close(fig); out.append(p)
    return out


def findings(r: Dict) -> str:
    """Facts only, each with its numbers. The interpretation is left to the analyst (see the prompts)."""
    q, c, bs, g = r["quarterly"], r["cash"], r["balance"], r["guidance"]
    L = ["# Findings (generated from the filings)", "",
         "Facts computed from Bending Spoons' SEC results releases. Every input figure, with its source link, is in "
         "`data/financials.csv` and the Excel 'Figures' sheet.", ""]
    lq = q.dropna(subset=["revenue_m"]).tail(1)
    if len(lq):
        x = lq.iloc[0]
        L += ["## 1. Growth: bought or organic?",
              f"- {x.period}: revenue ${x.revenue_m:,.0f}m, up {x.revenue_growth_yoy_pct}% year on year; organic growth "
              f"{x.organic_growth_pct}%, so about {x.acquired_growth_pct} points of the growth came from acquisitions."
              if pd.notna(x.revenue_growth_yoy_pct) and pd.notna(x.organic_growth_pct) else
              f"- {x.period}: revenue ${x.revenue_m:,.0f}m.", ""]
        orgs = q.dropna(subset=["organic_growth_pct"])
        if len(orgs) > 1:
            L += ["- Organic growth by quarter: " + ", ".join(f"{a} {b}%" for a, b in zip(orgs.period, orgs.organic_growth_pct)), ""]
        L += ["## 2. Profitability: IFRS vs adjusted",
              f"- {x.period}: operating margin {x.operating_margin_pct}% (IFRS) vs adjusted {x.adj_operating_margin_pct}%: "
              f"a {x.gap_adj_vs_gaap_pp}-point gap. Amortisation of acquired intangibles is {x.amortisation_pct_rev}% of "
              f"revenue and reorganisation costs {x.reorganisation_pct_rev}%.",
              f"- Interest coverage (operating income / interest expense): {x.interest_coverage_x}x.", ""]
    if len(c):
        y = c.iloc[-1]
        L += ["## 3. Does profit turn into cash?",
              f"- {y.period}: operating cash flow ${y.operating_cash_flow_m:,.0f}m, capex ${-y.capex_m:,.0f}m, free cash flow "
              f"${y.free_cash_flow_m:,.0f}m ({y.fcf_margin_pct}% of revenue); operating cash flow / net income = "
              f"{y.cash_conversion_ocf_to_net_income}x.",
              f"- Acquisitions cost ${-y.acquisitions_m:,.0f}m in the same period ({y.acquisitions_to_fcf_x}x free cash flow), "
              f"funded with ${y.debt_raised_m:,.0f}m of new debt; interest paid ${y.interest_paid_m:,.0f}m.", ""]
    if len(bs):
        z, a = bs.iloc[-1], bs.iloc[0]
        L += ["## 4. Debt and balance sheet",
              f"- Net debt ${a.net_debt_m:,.0f}m ({a.date}) -> ${z.net_debt_m:,.0f}m ({z.date}); debt / equity "
              f"{a.debt_to_equity_x}x -> {z.debt_to_equity_x}x.",
              f"- Goodwill and intangibles are {z.goodwill_intangibles_pct_assets}% of total assets.",
              f"- Net debt / annualised adjusted operating income: {z.net_debt_to_annualised_adj_op_income_x}x (proxy; the "
              f"company's own leverage ratio uses adjusted EBITDA).", ""]
    if g:
        L += ["## 5. Guidance"] + [f"- From the {d['release']} release: {d['target']} revenue ${d['revenue_low_m']:,.0f}m–"
                                   f"${d['revenue_high_m']:,.0f}m (midpoint ${d['midpoint_m']:,.0f}m)." for d in g]
        fy = [d for d in g if d["target"].upper().startswith("FY") or "fiscal" in d["target"].lower()
              or "year" in d["target"].lower()]
        h1 = c[c.period.str.startswith("H1")] if len(c) else c
        qr = q.set_index("period").revenue_m
        if fy:
            f, yr = fy[-1], fy[-1]["target"][-4:]
            done = sum(qr.get(f"Q{i} {yr}", 0) or 0 for i in (1, 2, 3))
            n_done = sum(1 for i in (1, 2, 3) if pd.notna(qr.get(f"Q{i} {yr}")))
            q3g = next((d["midpoint_m"] for d in g if d["target"] == f"Q3 {yr}"), None)
            if n_done == 3:
                L.append(f"- Implied Q4 {yr} revenue = FY midpoint − Q1–Q3 actual = ${f['midpoint_m'] - done:,.0f}m.")
            elif n_done == 2 and q3g:
                L.append(f"- Implied Q4 {yr} revenue = FY midpoint − (H1 actual + Q3 guidance midpoint) = "
                         f"${f['midpoint_m'] - done - q3g:,.0f}m.")
        L.append("")
    L += ["## Questions for the analyst (answer these in the memo, in your own words)",
          "1. Is 3% organic growth a problem for a company valued on its acquisition engine? What would you watch next quarter?",
          "2. Which adjustments between IFRS and adjusted operating income are truly one-off, and which recur every quarter?",
          "3. Free cash flow covers only a fraction of acquisition spend. What happens if debt markets tighten?",
          "4. Does the implied Q4 revenue look achievable given the quarterly run-rate and the pending acquisitions?",
          "5. If you were on the finance team, which single number would you want to improve first, and how?"]
    text = "\n".join(L) + "\n"
    (C.OUT / "findings.md").write_text(text)
    return text
