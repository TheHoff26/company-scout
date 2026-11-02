"""Offline test for scout.run.  Run: python tests/test_run.py"""
import json, sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scout.run import update  # noqa: E402

RSS = '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'

class R:
    def __init__(self, body="", status=200, url="", ctype="text/html"):
        self.status_code, self.url = status, url
        self.text = body if isinstance(body, str) else json.dumps(body)
        self.content = self.text.encode(); self.headers = {"Content-Type": ctype}
    def json(self): return json.loads(self.text)

class Web:
    def get(self, url, params=None, **kw):
        if url == "https://www.helen.fi/careers":
            return R('<a href="https://helen.wd3.myworkdayjobs.com/en-US/Helen">Open jobs</a>', url=url)
        if url.endswith("/services/rss/job/") and "jobs.neste.com" in url:
            return R(RSS)
        return R("", status=404, url=url)
    def post(self, url, json=None, **kw):
        if "helen.wd3" in url: return R({"total": 3, "jobPostings": []})
        return R("", status=404)

def test():
    data = {"companies": [
        {"id": "helen", "name": "Helen", "careers_url": "https://www.helen.fi/careers", "jobs": {"ats": None}, "private": {"iv": "x", "ct": "y"}},
        {"id": "nobody", "name": "Nobody Ltd", "careers_url": "", "jobs": {}},
        {"id": "neste", "name": "Neste", "jobs": {"ats": "successfactors", "url": "https://jobs.neste.com", "check": None}},
        {"id": "st1", "name": "St1", "jobs": {"ats": "linkedin"}},
        {"id": "old", "name": "Old", "jobs": {"ats": None, "detect_failed": "2026-11-01, no supported job system found"}},
    ]}
    today = date(2026, 11, 2)
    assert update(data, Web(), today, check=True)
    c = {x["id"]: x for x in data["companies"]}
    assert c["helen"]["jobs"]["ats"] == "workday" and c["helen"]["jobs"]["url"] == "https://helen.wd3.myworkdayjobs.com/Helen"
    assert c["helen"]["private"] == {"iv": "x", "ct": "y"}              # encrypted part untouched
    assert c["nobody"]["jobs"]["ats"] is None and "careers page" in c["nobody"]["jobs"]["detect_failed"]
    assert c["neste"]["jobs"]["check"] == {"date": "2026-11-02", "ok": True}
    assert c["st1"]["jobs"] == {"ats": "linkedin"}
    assert c["old"]["jobs"]["detect_failed"].startswith("2026-11-01")   # not retried within 7 days
    print(json.dumps(c["helen"]["jobs"]), json.dumps(c["nobody"]["jobs"]))

if __name__ == "__main__":
    test(); print("OK")
