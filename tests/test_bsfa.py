import json
from pathlib import Path

import pandas as pd
import pytest

from bsfa import analysis, config as C, dataset, outputs
from bsfa.extract import parse_number, parse_release, text_facts


def test_numbers():
    assert parse_number("(19,488") == -19488
    assert parse_number("704,155") == 704155
    assert parse_number("—") == 0.0
    assert parse_number("nm") is None


def test_parse_release_reads_split_cells_colspans_and_sections(q2_html):
    rows = pd.DataFrame(parse_release(q2_html, "Q2 2026", "u"))
    get = lambda st, li, p: rows[(rows.statement == st) & (rows.line_item == li) & (rows.period == p)].value.iloc[0]  # noqa: E731
    assert get("income_statement", "Revenue", "H1 2026") == 1305476
    assert get("income_statement", "Other expense (income)", "Q2 2026") == -19488
    assert get("balance_sheet", "Total assets", "2026-06-30") == 8055399
    assert get("cash_flow", "Purchase of intangible assets", "H1 2026") == 0.0
    eps = rows[rows.line_item.str.endswith(": Diluted") & (rows.unit == "usd_per_share")]
    assert set(eps.period) == {"Q2 2025", "Q2 2026", "H1 2025", "H1 2026"}
    assert rows[(rows.line_item == "Revenue") & (rows.statement == "income_statement")].unit.eq("usd_thousands").all()
    margin = rows[rows.line_item == "Adjusted Operating Income Margin"]
    assert margin.unit.eq("percent").all() and set(margin.value) == {49.0, 54.0}


def test_text_facts(q2_html):
    f = text_facts(q2_html)
    assert f["organic_growth_pct"] == 3.0
    assert any("$2.82 billion" in s for s in f["guidance"])


@pytest.fixture
def built(q2_html, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATA", tmp_path / "data")
    monkeypatch.setattr(C, "OUT", tmp_path / "out")
    p = tmp_path / "q2.htm"
    p.write_text(q2_html)
    df = dataset.build([{"quarter": "Q2 2026", "url": "https://sec/q2", "path": str(p), "date": "2026-08-13"}])
    return df, analysis.run(df)


def test_metrics_match_published_figures(built):
    _, r = built
    q = r["quarterly"].set_index("period")
    assert q.loc["Q1 2026", "revenue_m"] == 601.3          # H1 - Q2; Bending Spoons reported $601.3m for Q1 2026
    assert q.loc["Q2 2026", "revenue_growth_yoy_pct"] == 126.3
    assert q.loc["Q2 2026", "acquired_growth_pct"] == 123.3
    assert q.loc["Q2 2026", "adj_operating_margin_pct"] == 54.1
    bs = r["balance"].set_index("date")
    assert bs.loc["2026-06-30", "net_debt_m"] == 4088.1      # reported as about $4.09bn
    c = r["cash"].set_index("period")
    assert c.loc["H1 2026", "free_cash_flow_m"] == 250.3
    g = {d["target"]: d for d in r["guidance"]}
    assert g["fiscal 2026"]["midpoint_m"] == 2800.0 and g["Q3 2026"]["revenue_low_m"] == 733.0


def test_outputs(built):
    df, r = built
    xl = outputs.excel(df, r)
    assert Path(xl).exists()
    assert len(outputs.charts(r)) == 4
    text = outputs.findings(r)
    assert "organic growth 3.0%" in text and "Implied Q4 2026 revenue" in text


def test_latest_release_wins(q2_html, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "DATA", tmp_path / "data")
    a, b = tmp_path / "a.htm", tmp_path / "b.htm"
    a.write_text(q2_html)
    b.write_text(q2_html.replace("Q2 2026 results", "Q3 2026 results").replace("311,100", "311,000"))
    df = dataset.build([{"quarter": "Q2 2026", "url": "a", "path": str(a)}, {"quarter": "Q3 2026", "url": "b", "path": str(b)}])
    v = df[(df.line_item == "Revenue") & (df.period == "Q2 2025") & (df.statement == "income_statement")]
    assert len(v) == 1 and v.value.iloc[0] == 311000 and v.source_url.iloc[0] == "b"
    assert json.loads((C.DATA / "text_facts.json").read_text()).keys() == {"Q2 2026", "Q3 2026"}
