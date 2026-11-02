"""Maintains the job sources in docs/companies.json.

  python -m scout.run              detect sources for companies without one
  python -m scout.run --check      additionally test every existing source

Runs within a time budget (default 25 min). Results are saved after every
company, so a run that is stopped keeps its progress; the next run continues
with the companies still pending. Only the `jobs` part of a company is changed.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import date
from pathlib import Path

import requests

from .discover import _validate, detect
from .sources import USER_AGENT

log = logging.getLogger("scout")
DATA = Path(__file__).resolve().parent.parent / "docs" / "companies.json"
RETRY_DAYS = 7


def probe_session() -> requests.Session:
    """Plain session without automatic retries: probes must fail fast."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


def _needs_detection(jobs: dict, today: date) -> bool:
    if jobs.get("ats"):
        return False
    failed = jobs.get("detect_failed")
    if not failed:
        return True
    try:
        return (today - date.fromisoformat(failed[:10])).days >= RETRY_DAYS
    except ValueError:
        return True


def _save(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update(data: dict, session, today: date, check: bool, budget_s: float = 1500,
           save=lambda: None, clock=time.monotonic) -> bool:
    start, changed = clock(), False
    companies = data.get("companies", [])
    todo = [c for c in companies if _needs_detection(c.get("jobs") or {}, today)]
    todo.sort(key=lambda c: 0 if c.get("careers_url") else 1)   # careers page first: faster, more reliable
    for c in todo:
        if clock() - start > budget_s:
            log.info("time budget used – %d companies left for the next run", len(todo) - todo.index(c))
            break
        res = detect(session, c.get("name", ""), c.get("careers_url") or None)
        stamp = f"{today.isoformat()}, {res['how']}"
        if res["ats"] == "linkedin":
            c["jobs"] = {"ats": None, "detect_failed": stamp, "check": None}
            log.info("%-30s -> not found", c.get("name"))
        else:
            c["jobs"] = {"ats": res["ats"], ("url" if "url" in res else "id"): res.get("url") or res.get("id"),
                         "detected": stamp, "check": {"date": today.isoformat(), "ok": True}}
            log.info("%-30s -> %s", c.get("name"), res["ats"])
        changed = True
        save()
    if check:
        for c in companies:
            jobs = c.get("jobs") or {}
            if jobs.get("ats") in (None, "linkedin") or (jobs.get("check") or {}).get("date") == today.isoformat():
                continue
            if clock() - start > budget_s:
                log.info("time budget used – remaining checks next run")
                break
            ok = _validate(session, {"ats": jobs["ats"], "url": jobs.get("url"), "id": jobs.get("id")})
            jobs["check"] = {"date": today.isoformat(), "ok": ok}
            log.info("%-30s check %s", c.get("name"), "ok" if ok else "FAILED")
            changed = True
            save()
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="also test every existing job source")
    ap.add_argument("--budget-minutes", type=float, default=25)
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = Path(args.data)
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = update(data, probe_session(), date.today(), args.check, args.budget_minutes * 60,
                     save=lambda: _save(path, data))
    log.info("companies.json updated" if changed else "nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
