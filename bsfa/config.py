"""Settings for the Bending Spoons financial analysis."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"            # downloaded filings (cached, not committed)
DATA = ROOT / "data"                   # extracted, source-linked figures (committed)
OUT = ROOT / "output"                  # metrics, Excel workbook, charts, findings (committed)

COMPANY = "Bending Spoons S.p.A."
CIK = "2004711"                        # SEC Central Index Key
TICKER = "BSP"
# SEC asks automated tools to identify themselves: https://www.sec.gov/os/accessing-edgar-data
USER_AGENT = os.environ.get("SEC_USER_AGENT", "Chrish Pep Felix A chrishpepfelixa@gmail.com")
SLEEP = 0.25                           # stay well under SEC's 10 requests/second
