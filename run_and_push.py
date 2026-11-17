#!/usr/bin/env python3
"""One command on the Mac (system Python 3.9 is fine: standard library only).

  python3 run_and_push.py --run        # download Bending Spoons' SEC filings, extract, analyse, write outputs (free)
  python3 run_and_push.py --push-only  # commit + push to GitHub (after you have written MEMO.md)
"""
import base64
import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv312"
PY = VENV / "bin" / "python"
OWNER, REPO = "ChrishA-tech", "bending-spoons-financial-analysis"


def sh(cmd, check=True):
    print("+", " ".join(map(str, cmd)))
    return subprocess.run(list(map(str, cmd)), cwd=ROOT, check=check).returncode


def setup():
    u = shutil.which("uv") or str(Path.home() / ".local/bin/uv")
    if not Path(u).exists():
        sh(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"])
    if not PY.exists():
        sh([u, "venv", "--python", "3.12", VENV])
    sh([u, "pip", "install", "--python", PY, "-r", "requirements.txt"])


def api(path, token, method="GET", body=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method,
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {}


def push():
    token = os.environ.get("GITHUB_TOKEN") or getpass.getpass("GitHub token (classic, repo scope; input hidden): ").strip()
    st, me = api("/user", token)
    if st != 200 or me.get("login") != OWNER:
        sys.exit(f"Token belongs to {me.get('login')!r}, expected {OWNER}. Stopping.")
    if api(f"/repos/{OWNER}/{REPO}", token)[0] == 404:
        api("/user/repos", token, "POST", {"name": REPO, "private": False, "description":
            "Bending Spoons' financial statements from SEC filings: organic vs acquired growth, US GAAP vs adjusted "
            "margins, cash conversion, acquisition debt and guidance. Every figure source-linked."})
        api(f"/repos/{OWNER}/{REPO}/topics", token, "PUT", {"names": [
            "financial-analysis", "financial-statements", "sec-edgar", "python", "pandas", "excel", "data-analysis"]})
    if not (ROOT / ".git").exists():
        sh(["git", "init", "-b", "main"])
    sh(["git", "add", "-A"])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
        sh(["git", "-c", "user.name=Chrish Pep Felix A", "-c", "user.email=chrishpepfelixa@gmail.com", "commit", "-m",
            "Bending Spoons financial analysis: figures, metrics, workbook, findings and memo"])
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    r = subprocess.run(["git", "-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth}", "push",
                        f"https://github.com/{OWNER}/{REPO}.git", "HEAD:main"], cwd=ROOT, capture_output=True, text=True)
    print((r.stdout + r.stderr).replace(token, "***").replace(auth, "***"))
    if r.returncode:
        sys.exit("Push failed (see above).")
    print(f"Done: https://github.com/{OWNER}/{REPO}\nNow delete the token at https://github.com/settings/tokens")


def main():
    a = set(sys.argv[1:])
    if "--run" in a:
        setup()
        sh([PY, "-m", "pytest", "-q"])
        sh([PY, "-m", "bsfa.run"])
        print("\nDone. Open output/bending_spoons_analysis.xlsx and output/findings.md, then write MEMO.md.")
    elif "--push-only" in a:
        push()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
