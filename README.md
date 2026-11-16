# What Bending Spoons' numbers say

An analysis of Bending Spoons S.p.A. (Nasdaq: BSP) built straight from its SEC filings. A Python pipeline downloads
every quarterly results release (Form 6-K, exhibit 99.1), extracts the income statement, balance sheet, cash flow
statement and non-GAAP reconciliations into one table **with a link to the source filing for every figure**, and
answers five questions:

1. **Growth:** how much is organic, and how much is bought through acquisitions?
2. **Profitability:** how far apart are IFRS and adjusted operating margins, and what fills the gap?
3. **Cash:** does profit turn into cash, and how does free cash flow compare with acquisition spend?
4. **Debt:** how much debt funds the acquisitions, and how well do earnings cover the interest?
5. **Guidance:** what does full-year guidance imply for the rest of the year?

My conclusions are in **[MEMO.md](MEMO.md)**. The numbers behind them are below and in
`output/bending_spoons_analysis.xlsx`.

```mermaid
flowchart LR
  A[SEC EDGAR<br/>6-K results releases] --> B[Table extraction<br/>split cells, colspans, negatives]
  B --> C[data/financials.csv<br/>one row per figure + source URL]
  C --> D[Metrics<br/>growth, margins, cash, debt, guidance]
  D --> E[Excel workbook + charts]
  D --> F[findings.md]
  F --> G[MEMO.md<br/>my interpretation]
```

## Results

<!-- RESULTS:START -->
Run `python3 run_and_push.py --run` to fill this in.
<!-- RESULTS:END -->

## How the numbers are checked

- Every figure in `data/financials.csv` keeps the URL of the filing it came from; the Excel "Figures" sheet links to it.
- When a figure appears in several releases (prior-year comparatives), the latest release wins, so restatements are used.
- Q1 figures not reported on their own are derived as H1 − Q2 and match the company's published Q1 numbers.
- Tests check the extractor on SEC-style HTML (split "$" cells, negatives in brackets, column spans, section headers)
  and check computed metrics against figures Bending Spoons published.

## Definitions

| Metric | Definition |
|---|---|
| Growth from acquisitions | Reported year-on-year revenue growth minus the company's stated organic growth |
| Gap, adjusted vs IFRS | (Adjusted operating income − operating income) / revenue |
| Free cash flow | Operating cash flow − purchases of property, plant, equipment and intangible assets |
| Cash conversion | Operating cash flow / net income |
| Net debt | Long-term debt (current + non-current) − cash and cash equivalents |
| Leverage (proxy) | Net debt / (latest quarter's adjusted operating income × 4); the company's own ratio uses adjusted EBITDA |
| Interest coverage | Operating income / interest expense |

## Run it

```
python3 run_and_push.py --run        # free: downloads public SEC filings, about 1 minute
```

Data: public SEC EDGAR filings by Bending Spoons S.p.A. (CIK 2004711). This is an independent student analysis, not
investment advice, and is not affiliated with Bending Spoons.
