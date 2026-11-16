"""Download the filings, extract the figures, compute metrics, write the workbook, charts, findings and README results."""
import re

from . import analysis, config as C, dataset, outputs

START, END = "<!-- RESULTS:START -->", "<!-- RESULTS:END -->"


def readme(r):
    q = r["quarterly"].dropna(subset=["revenue_m"])
    cols = ["period", "revenue_m", "revenue_growth_yoy_pct", "organic_growth_pct", "operating_margin_pct",
            "adj_operating_margin_pct", "net_margin_pct", "interest_coverage_x"]
    head = ["Quarter", "Revenue ($m)", "Growth YoY", "Organic", "Op. margin", "Adj. op. margin", "Net margin", "Interest cover"]
    fmt = lambda v, pct: "n/a" if v != v or v is None else (f"{v:.1f}%" if pct else (f"{v:,.1f}" if isinstance(v, float) else str(v)))  # noqa: E731,E501
    rows = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for _, x in q[cols].iterrows():
        rows.append("| " + " | ".join([x.period, fmt(x.revenue_m, False)] + [fmt(x[c], True) for c in cols[2:7]]
                                      + [fmt(x.interest_coverage_x, False) + "x"]) + " |")
    findings = (C.OUT / "findings.md").read_text().split("\n", 4)[-1]
    block = "\n".join(rows) + "\n\n![Growth](output/growth_organic_vs_acquired.png)\n![Margins](output/margins.png)\n" \
            "![Cash](output/cash_vs_acquisitions.png)\n\n" + findings
    p = C.ROOT / "README.md"
    txt = p.read_text()
    p.write_text(re.sub(re.escape(START) + ".*" + re.escape(END), f"{START}\n{block}\n{END}", txt, flags=re.S))


def main():
    df = dataset.build()
    r = analysis.run(df)
    print("workbook:", outputs.excel(df, r))
    outputs.charts(r)
    print(outputs.findings(r))
    readme(r)


if __name__ == "__main__":
    main()
