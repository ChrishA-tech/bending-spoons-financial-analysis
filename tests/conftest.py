"""A results release in SEC's HTML style (split "$" and ")" cells, colspans), built from Bending Spoons' Q2 2026 6-K."""
import pytest


def _num_cells(v):
    if v is None:
        return '<td></td><td></td><td></td>'
    if isinstance(v, str):
        return f'<td></td><td style="text-align:right">{v}</td><td></td>'
    neg = v < 0
    s = f"{abs(v):,}" if isinstance(v, int) else f"{abs(v):.2f}"
    return f'<td>$</td><td style="text-align:right">{"(" if neg else ""}{s}</td><td>{")" if neg else ""}</td>'


def _table(title, unit, periods, years, rows, change=False):
    """periods: list of (phrase, n_years) for a colspan header row; years: list of year strings."""
    h1 = f"<tr><td></td>" + "".join(f'<td colspan="{3 * n}">{p}</td>' for p, n in periods) + ("<td colspan=3></td>" if change else "") + "</tr>"
    h2 = f"<tr><td>{unit}</td>" + "".join(f'<td colspan="3">{y}</td>' for y in years) + ("<td colspan=3>Change</td>" if change else "") + "</tr>"
    body = ""
    for r in rows:
        if len(r) == 1:
            body += f"<tr><td>{r[0]}</td></tr>"
            continue
        label, vals = r[0], r[1:]
        cells = "".join(_num_cells(v) for v in vals)
        body += f"<tr><td>{label}</td>{cells}</tr>"
    return f"<p><b>{title}</b></p><table>{h1}{h2}{body}</table>"


def q2_2026_html():
    t3 = [("Three months ended June 30,", 2)]
    parts = [
        "<p>Bending Spoons announces Q2 2026 results</p>",
        "<p>Revenue grew by $393 million (126%). Organic revenue growth<sup>4</sup> was 3% in Q2 2026, with Tractive "
        "and WeTransfer making the largest contributions.</p>",
        "<p>For Q3 2026, we expect revenue of between $733 million and $745 million. For fiscal 2026, we expect revenue "
        "of between $2.78 billion and $2.82 billion.</p>",
        _table("Operating results (unaudited)", "Thousands, except percentages and per-share amounts", t3, ["2025", "2026"], [
            ("Revenue", 311100, 704155, "126 %"), ("Gross profit", 204485, 463621, "127 %"),
            ("Operating income", 100617, 240251, "139 %"),
            ("Operating income as a percentage of revenue", "32 %", "34 %", "2 pp"),
            ("Net income", 65253, 176967, "171 %"), ("Diluted earnings per share", 0.11, 0.28, "163 %")], change=True),
        _table("Adjusted measures", "Thousands, except percentages and per-share amounts", t3, ["2025", "2026"], [
            ("Adjusted Operating Income", 152525, 381149, "150 %"),
            ("Adjusted Operating Income Margin", "49 %", "54 %", "5 pp")], change=True),
        _table("Condensed consolidated balance sheet (unaudited)", "Thousands", [], ["December 31, 2025", "June 30, 2026"], [
            ("ASSETS",), ("Cash and cash equivalents", 629944, 792950), ("Accounts receivable, net", 144593, 278767),
            ("Total current assets", 918664, 1351702), ("Goodwill", 2423570, 4146212),
            ("Intangible assets, net", 1077974, 2156607), ("Total assets", 4757495, 8055399),
            ("LIABILITIES AND SHAREHOLDERS' EQUITY",), ("Long-term debt, current", 415260, 794141),
            ("Deferred revenue, current", 450499, 583265), ("Total current liabilities", 1118530, 2112654),
            ("Long-term debt, non-current", 2255622, 4086939), ("Deferred revenue, non-current", 214, 38404),
            ("Total liabilities", 3762632, 6796987), ("Total shareholders' equity", 994863, 1258412)]),
        _table("Condensed consolidated income statement (unaudited)", "Thousands, except per-share amounts",
               [("Three months ended June 30,", 2), ("Six months ended June 30,", 2)], ["2025", "2026", "2025", "2026"], [
            ("Revenue", 311100, 704155, 570046, 1305476), ("Cost of revenue", 106615, 240534, 200118, 433651),
            ("Gross profit", 204485, 463621, 369928, 871825),
            ("Research and development expense", 19398, 58204, 63157, 152599),
            ("Sales and marketing expense", 30696, 72679, 68014, 131230),
            ("General and administrative expense", 53774, 92488, 142754, 227573),
            ("Operating income", 100617, 240251, 96003, 360422), ("Interest expense", 35733, 108970, 55049, 202154),
            ("Other expense (income)", 2745, -19488, 6734, -68832), ("Income before tax", 62139, 150769, 34220, 227101),
            ("Net income (loss)", 65253, 176967, -46953, 204433),
            ("Earnings (loss) per share attributable to Bending Spoons shareholders:",),
            ("Basic", 0.11, 0.30, -0.08, 0.34), ("Diluted", 0.11, 0.28, -0.08, 0.32),
            ("Weighted average shares used to compute earnings (loss) per share:",),
            ("Basic", 577681, 600821, 577673, 599253), ("Diluted", 613746, 634748, 577673, 635046)]),
        _table("Condensed consolidated statement of cash flows (unaudited)", "Thousands",
               [("Six months ended June 30,", 2)], ["2025", "2026"], [
            ("Cash flows from operating activities:",), ("Net income (loss)", -46953, 204433),
            ("Equity compensation expense", 27885, 42984), ("Net cash from operating activities", 87733, 254240),
            ("Acquisitions of businesses net of cash, cash equivalents, and restricted cash acquired", -575228, -2286259),
            ("Purchase of property, plant, and equipment", -282, -3969), ("Purchase of intangible assets", -53, "—"),
            ("Net cash from investing activities", -575563, -2290228), ("Proceeds from issuance of debt", 1012901, 2566532),
            ("Interests paid", 49737, 161153)]),
        _table("Reconciliation of operating income to Adjusted Operating Income", "Thousands, except percentages", t3,
               ["2025", "2026"], [
            ("Operating income", 100617, 240251, "139 %"),
            ("Amortization and impairment of acquired intangible assets", 36070, 82310, "128 %"),
            ("Transaction-related expense", 705, 6553, "829 %"), ("Reorganization-related expense", 11338, 50799, "348 %"),
            ("Other items not indicative of core or ongoing operating performance", 3795, 1236, "(67) %"),
            ("Adjusted Operating Income", 152525, 381149, "150 %")], change=True),
    ]
    return "<html><body>" + "".join(parts) + "</body></html>"


@pytest.fixture
def q2_html():
    return q2_2026_html()
