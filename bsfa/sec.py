"""Download Bending Spoons' quarterly results releases (Form 6-K, exhibit 99.1) from SEC EDGAR.

Standard library only. Files are cached in data/raw/, so re-runs do not hit SEC again.
"""
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Dict, List

from . import config as C

ARCHIVES = f"https://www.sec.gov/Archives/edgar/data/{C.CIK}"


def get(url: str, cache: Path = None) -> bytes:
    if cache and cache.exists():
        return cache.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": C.USER_AGENT, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read()
    time.sleep(C.SLEEP)
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(body)
    return body


def filings(form: str = "6-K") -> List[Dict]:
    """All filings of one form type, newest first."""
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{int(C.CIK):010d}.json",
                         C.RAW / "submissions.json"))
    rec = sub["filings"]["recent"]
    out = []
    for i, f in enumerate(rec["form"]):
        if f == form:
            out.append({"form": f, "accession": rec["accessionNumber"][i], "date": rec["filingDate"][i],
                        "primary": rec["primaryDocument"][i]})
    return out


def results_releases() -> List[Dict]:
    """6-K filings whose exhibit is a quarterly results release ("announces Qn YYYY results")."""
    found = []
    for f in filings("6-K"):
        acc = f["accession"].replace("-", "")
        try:
            idx = json.loads(get(f"{ARCHIVES}/{acc}/index.json", C.RAW / acc / "index.json"))
        except Exception as e:                     # noqa: BLE001 - one bad filing must not stop the run
            print("skip", f["accession"], e)
            continue
        names = [it["name"] for it in idx["directory"]["item"]]
        cands = [n for n in names if re.search(r"ex-?99[-_.]?1\b|ex99-?1", n, re.I) and n.lower().endswith((".htm", ".html"))]
        for name in cands:
            url = f"{ARCHIVES}/{acc}/{name}"
            html = get(url, C.RAW / acc / name).decode("utf-8", "replace")
            m = re.search(r"announces\s+(Q[1-4])\s+(\d{4})\s+results", re.sub(r"<[^>]+>", " ", html), re.I)
            if m:
                found.append({**f, "quarter": f"{m.group(1).upper()} {m.group(2)}", "url": url,
                              "path": str(C.RAW / acc / name)})
                break
    return sorted(found, key=lambda x: x["date"])


if __name__ == "__main__":
    for r in results_releases():
        print(r["date"], r["quarter"], r["url"])
