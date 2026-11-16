"""Download every results release and build data/financials.csv (one source-linked row per figure)."""
import json
from pathlib import Path

import pandas as pd

from . import config as C
from .extract import parse_release, text_facts

COLS = ["release", "statement", "line_item", "period", "value", "unit", "source_url", "table"]


def build(releases=None) -> pd.DataFrame:
    if releases is None:
        from .sec import results_releases
        releases = results_releases()
    if not releases:
        raise SystemExit("No results releases found on SEC EDGAR.")
    rows, facts = [], {}
    for r in releases:
        html = Path(r["path"]).read_text(encoding="utf-8", errors="replace")
        got = parse_release(html, r["quarter"], r["url"])
        print(f"{r['quarter']}: {len(got)} figures from {r['url']}")
        rows += got
        facts[r["quarter"]] = {**text_facts(html), "url": r["url"], "filed": r.get("date")}
    df = pd.DataFrame(rows, columns=COLS)
    order = {q: i for i, q in enumerate(sorted(facts, key=lambda q: (q.split()[1], q.split()[0])))}
    df["_o"] = df["release"].map(order)
    # The same figure appears in several releases (prior-year comparatives); keep the latest release's value.
    df = (df.sort_values("_o").drop_duplicates(["statement", "line_item", "period", "unit"], keep="last")
          .drop(columns="_o").sort_values(["statement", "line_item", "period"]))
    C.DATA.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.DATA / "financials.csv", index=False)
    (C.DATA / "text_facts.json").write_text(json.dumps(facts, indent=2))
    return df
