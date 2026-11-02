"""Maintains the job sources in docs/companies.json.

  python -m scout.run            detect sources for companies without one
  python -m scout.run --check    additionally test every source (weekly)

Only the `jobs` part of a company is changed; everything else (including the
encrypted contacts) is left exactly as it is.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from .discover import _validate, detect
from .sources import make_session

log = logging.getLogger("scout")
DATA = Path(__file__).resolve().parent.parent / "docs" / "companies.json"
RETRY_DAYS = 7


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


def update(data: dict, session, today: date, check: bool) -> bool:
    changed = False
    for c in data.get("companies", []):
        jobs = c.setdefault("jobs", {}) or {}
        c["jobs"] = jobs
        if _needs_detection(jobs, today):
            res = detect(session, c.get("name", ""), c.get("careers_url") or None)
            stamp = f"{today.isoformat()}, {res['how']}"
            if res["ats"] == "linkedin":
                new = {"ats": None, "detect_failed": stamp, "check": None}
            else:
                new = {"ats": res["ats"], ("url" if "url" in res else "id"): res.get("url") or res.get("id"),
                       "detected": stamp, "check": {"date": today.isoformat(), "ok": True}}
            log.info("%-30s -> %s", c.get("name"), stamp if res["ats"] == "linkedin" else res["ats"])
            c["jobs"] = new
            changed = True
        elif check and jobs.get("ats") not in (None, "linkedin"):
            target = {"ats": jobs["ats"], "url": jobs.get("url"), "id": jobs.get("id")}
            ok = _validate(session, target)
            jobs["check"] = {"date": today.isoformat(), "ok": ok}
            log.info("%-30s check %s", c.get("name"), "ok" if ok else "FAILED")
            changed = True
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="also test every existing job source")
    ap.add_argument("--data", default=str(DATA))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    path = Path(args.data)
    data = json.loads(path.read_text(encoding="utf-8"))
    if update(data, make_session(), date.today(), args.check):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log.info("companies.json updated")
    else:
        log.info("nothing to do")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
