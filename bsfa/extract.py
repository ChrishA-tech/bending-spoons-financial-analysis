"""Turn the tables in a results release into tidy, source-linked rows.

One row per figure: release, statement, line item, period, value, unit, source URL. Handles the usual SEC HTML quirks:
"$" and ")" in their own cells, column spans on header rows, negative numbers in parentheses, "—" for zero, and
section-header rows (e.g. "Earnings per share:" followed by "Basic" / "Diluted").
"""
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

MONTH_Q = {"march": "Q1", "june": "Q2", "september": "Q3", "december": "Q4"}
SPAN = {"three": "Q", "six": "H1", "nine": "9M", "twelve": "FY"}
STATEMENTS = [  # (key, words that identify the table title)
    ("operating_results", ["operating results"]),
    ("adjusted_measures", ["adjusted measures"]),
    ("balance_sheet", ["balance sheet"]),
    ("income_statement", ["income statement", "statement of operations", "statements of operations"]),
    ("cash_flow", ["cash flows", "cash flow"]),
    ("recon_operating_income", ["reconciliation of operating income"]),
    ("recon_net_income", ["reconciliation of net income"]),
    ("recon_eps", ["reconciliation of diluted"]),
    ("original_vs_revised", ["original vs", "original versus"]),
    ("guidance", ["outlook", "guidance"]),
]
YEAR = re.compile(r"\b(19|20)\d{2}\b")
NUM = re.compile(r"\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?\s*(?:%|pp)?|(?<!\w)[—–](?!\w)|\bnm\b")


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).replace("\xa0", " ").strip()


def _grid(table) -> List[List[str]]:
    """Rows expanded by colspan, so header cells line up with value cells by position."""
    rows = []
    for tr in table.find_all("tr"):
        row = []
        for td in tr.find_all(["td", "th"]):
            span = int(td.get("colspan", 1) or 1)
            row.extend([_text(td)] + [None] * (span - 1))     # None = covered by the cell to the left
        if any(c for c in row):
            rows.append(row)
    return rows


def parse_number(tok: str) -> Optional[float]:
    t = tok.strip()
    if t in ("—", "–"):
        return 0.0
    if t.lower() == "nm":
        return None
    neg = "(" in t or t.startswith("-")
    digits = re.sub(r"[^\d.]", "", t)
    if not digits or digits == ".":
        return None
    v = float(digits)
    return -v if neg else v


def _title(table) -> str:
    """Nearest short text before the table (its caption in these releases)."""
    for s in table.find_all_previous(string=True):
        t = re.sub(r"\s+", " ", s).strip()
        if len(t) > 3 and not s.find_parent("table"):
            return t[:200]
    return ""


def classify(title: str, labels: List[str]) -> str:
    low = title.lower()
    for key, words in STATEMENTS:
        if any(w in low for w in words):
            return key
    joined = " | ".join(labels).lower()
    if "total assets" in joined:
        return "balance_sheet"
    if "net cash from operating" in joined:
        return "cash_flow"
    if "cost of revenue" in joined:
        return "income_statement"
    return "other"


def _period_label(phrase: str, year: str) -> str:
    p = (phrase or "").lower()
    month = next((m for m in MONTH_Q if m in p), None)
    span = next((v for k, v in SPAN.items() if k in p), None)
    if "year ended" in p:
        span = "FY"
    if span == "Q" and month:
        return f"{MONTH_Q[month]} {year}"
    if span in ("H1", "9M", "FY"):
        return f"{span} {year}"
    if month:                      # a point-in-time date (balance sheet)
        mm = {"march": "03-31", "june": "06-30", "september": "09-30", "december": "12-31"}[month]
        return f"{year}-{mm}"
    return year


def _columns(grid: List[List[str]]) -> (Dict[int, str], int):
    """Map grid position -> period label, using the header rows above the first data row."""
    period_row, year_row, start = None, None, 0
    for i, row in enumerate(grid[:6]):
        cells = [c for c in row if c]
        if not cells:
            continue
        if any("ended" in c.lower() for c in cells) and not any(NUM.fullmatch(c or "") for c in cells[1:]):
            period_row = row
        if sum(bool(YEAR.search(c)) for c in cells) >= 1 and all(
                YEAR.search(c) or c.lower() in ("change", "") or "thousand" in c.lower() or "million" in c.lower()
                or "per-share" in c.lower() or "ended" in c.lower() for c in cells):
            year_row, start = row, i + 1
            if any("ended" in c.lower() for c in cells) and period_row is None:
                period_row = row
            break
    cols = {}
    if year_row is None:
        return cols, 0
    for pos, cell in enumerate(year_row):
        if not cell or not YEAR.search(cell):
            continue
        year = YEAR.search(cell).group(0)
        phrase = cell if any(m in cell.lower() for m in MONTH_Q) else ""
        if not phrase and period_row:
            j = pos                                   # the period cell covering this position (colspan-aware)
            while j >= 0 and (j >= len(period_row) or period_row[j] is None or period_row[j] == ""):
                j -= 1
            phrase = period_row[j] if j >= 0 and j < len(period_row) and period_row[j] else ""
            if not phrase:                            # no colspan info: nearest period phrase to the left
                phrase = next((c for c in reversed(period_row[:pos + 1]) if c and "ended" in c.lower()), "")
        cols[pos] = _period_label(phrase, year)
    return cols, start


def _unit(text: str) -> str:
    low = text.lower()
    return "millions" if "millions" in low and "thousand" not in low else "thousands"


def parse_release(html: str, release: str, url: str) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for t_i, table in enumerate(soup.find_all("table")):
        grid = _grid(table)
        if len(grid) < 3:
            continue
        cols, start = _columns(grid)
        if not cols:
            continue
        periods = [cols[p] for p in sorted(cols)]
        labels = [next((c for c in r if c), "") for r in grid[start:]]
        statement = classify(_title(table), labels)
        unit_text = " ".join(c for r in grid[:start] for c in r if c)
        scale = _unit(unit_text)
        section = ""
        for row in grid[start:]:
            cells = [c for c in row if c is not None]
            label = next((c for c in cells if re.search(r"[A-Za-z]{2}", c) and not NUM.fullmatch(c)), "")
            if not label:
                continue
            rest = " ".join(c for c in cells if c and c != label).replace("$", " ")
            toks = NUM.findall(rest)
            pct_row = "percentage" in label.lower() or "margin" in label.lower()
            vals = [x for x in toks if (x.strip().endswith("%") if pct_row else not x.strip().endswith(("%", "pp")))]
            if not vals:
                section = label.rstrip(":")
                continue
            name = f"{section}: {label}" if section and label.lower() in ("basic", "diluted") else label
            low = name.lower()
            per_share_table = unit_text.lower().lstrip().startswith("per-share")
            unit = ("percent" if pct_row
                    else "shares_thousands" if "weighted" in low
                    else "usd_per_share" if ("per share" in low or per_share_table)
                    else f"usd_{scale}")
            for period, tok in zip(periods, vals):
                v = parse_number(tok)
                if v is None:
                    continue
                if unit == "usd_millions":
                    v, unit_o = v * 1000, "usd_thousands"
                else:
                    unit_o = unit
                out.append({"release": release, "statement": statement, "table": t_i, "line_item": name,
                            "period": period, "value": v, "unit": unit_o, "source_url": url})
    return out


def text_facts(html: str) -> Dict[str, object]:
    """Facts stated in prose: organic growth and guidance (kept with the sentence they came from)."""
    text = re.sub(r"\s+", " ", BeautifulSoup(html, "lxml").get_text(" "))
    facts = {"organic_growth_pct": None, "organic_sentence": None, "guidance": []}
    m = re.search(r"([^.]*organic revenue growth\W*\d?\s*was\s*(-?\d+(?:\.\d+)?)\s*%[^.]*\.)", text, re.I)
    if m:
        facts["organic_growth_pct"], facts["organic_sentence"] = float(m.group(2)), m.group(1).strip()
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text):
        if re.search(r"expect|forecast|outlook|guidance", s, re.I) and re.search(r"\$[\d.,]+\s*(?:million|billion)", s):
            facts["guidance"].append(s.strip()[:400])
    return facts
