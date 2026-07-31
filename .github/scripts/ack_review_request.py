"""Build the automatic first reply to a review-request issue.

What this does and does not do: it does NOT write the review. The review is AI-assisted work
a person still checks, so it cannot be posted unattended. What it removes is the dead time
around the review, which is where orders actually die — a buyer pays, opens an issue with a
URL that 404s, and finds out hours later.

Clause 2 of TERMS.md starts the 24-hour clock at "the later of: Stripe confirming your
payment, and us having a file URL that resolves publicly", and clause 3 allows exactly one
request for a replacement URL. So checking the URL the moment the issue opens is not a nicety:
it is the step that starts the buyer's clock, and doing it in seconds instead of hours is
worth more to them than anything else that can be automated here.

    python3 ack_review_request.py            # reads ISSUE_BODY from the environment
    python3 ack_review_request.py --selftest  # logic only, no network

The issue body arrives through the environment, never through argv or a shell interpolation —
`${{ github.event.issue.body }}` pasted into a run: line is a command-injection hole, and this
repo takes text from strangers by design.
"""
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TERMS = "https://github.com/zitacron/zitacron-code-review/blob/main/TERMS.md"
MAX_LINES = 300
MAX_BYTES = 2_000_000
UA = "zitacron-code-review-bot (+https://github.com/zitacron/zitacron-code-review)"


def field(body: str, label: str) -> str | None:
    """Pull one value out of a GitHub issue-form body ('### Label\\n\\nvalue')."""
    m = re.search(rf"^###\s+{re.escape(label)}\s*$\n+(.*?)(?=\n###\s|\Z)",
                  body or "", re.M | re.S)
    if not m:
        return None
    val = m.group(1).strip()
    return None if not val or val == "_No response_" else val


def raw_url(url: str) -> str:
    """github.com/o/r/blob/ref/path -> raw.githubusercontent.com/o/r/ref/path."""
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/blob/(.+)$", url.strip())
    return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else url


def fetch(url: str):
    """(status, n_lines) — status is an int, or a string describing why there is no int."""
    try:
        req = urllib.request.Request(raw_url(url), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(MAX_BYTES).decode("utf-8", "replace").count("\n") + 1
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:                      # DNS, TLS, timeout, bad scheme
        return type(e).__name__, None


def compose(body: str, status, lines, now: datetime) -> str:
    """The comment. Pure, so --selftest covers every branch without a network or a runner."""
    url = field(body, "Public URL of the file")
    due = (now + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M UTC")
    out = ["Thanks — this thread is where your review gets posted. Not email.", ""]

    if url is None:
        out += ["I could not find a file URL in this issue, so nothing is checked yet. "
                "Post one public URL (one file, 300 lines maximum) and the clock starts.", ""]
    elif status == 200 and lines is not None and lines <= MAX_LINES:
        out += [f"**Your file resolves publicly — {lines} lines, inside the 300-line limit.**",
                "",
                "Under [clause 2 of the terms]({0}) the 24-hour clock runs from the later of "
                "Stripe confirming your payment and this URL resolving. The URL half is done. "
                "If your payment is already confirmed, the review is due by **{1}**; if you "
                "have not paid yet, the clock starts when Stripe confirms.".format(TERMS, due),
                ""]
    elif status == 200 and lines is not None:
        out += [f"**This file is {lines} lines, over the 300-line limit.**",
                "",
                "Clause 3: larger files are refunded, not truncated — I will not review the "
                "first 300 lines and call it done. Post a shorter file, or a specific section "
                "as its own file, and we proceed. If you have paid and would rather not, say "
                "so here and it is refunded in full.", ""]
    else:
        out += [f"**That URL did not resolve for me — signed-out fetch returned `{status}`.**",
                "",
                "The review cannot start until it does, and clause 2 means your 24-hour clock "
                "has not started either, so you have lost no time. Clause 3 lets me ask once "
                "for a replacement: post a working public URL here. If none arrives and you "
                "have paid, clause 5 is a full refund.", ""]

    out += ["Up to three findings, each citing a line. If the file is sound you get a written "
            "note of what was examined and why it holds, plus one further file reviewed free "
            "(clause 4).",
            "",
            f"Full terms and your refund rights: {TERMS}",
            "",
            "<sub>Posted automatically when this issue opened. The review itself is written "
            "by a person, not by this bot.</sub>"]
    return "\n".join(out)


def selftest():
    now = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    body = ("### Public URL of the file\n\nhttps://github.com/o/r/blob/main/a.py\n\n"
            "### Language / runtime\n\nPython 3.12\n\n"
            "### What is this file supposed to do?\n\nParse logs.\n\n"
            "### What are you worried about?\n\n_No response_\n")
    assert field(body, "Public URL of the file") == "https://github.com/o/r/blob/main/a.py"
    assert field(body, "Language / runtime") == "Python 3.12"
    assert field(body, "What are you worried about?") is None      # _No response_ is not a value
    assert field(body, "Nonexistent") is None
    assert raw_url("https://github.com/o/r/blob/main/a.py") == \
        "https://raw.githubusercontent.com/o/r/main/a.py"
    assert raw_url("https://example.com/a.py") == "https://example.com/a.py"

    ok = compose(body, 200, 120, now)
    assert "120 lines, inside the 300-line limit" in ok and "2026-08-01 12:00 UTC" in ok
    big = compose(body, 200, 900, now)
    assert "over the 300-line limit" in big and "refunded, not truncated" in big
    dead = compose(body, 404, None, now)
    assert "`404`" in dead and "has not started either" in dead
    none = compose("", None, None, now)
    assert "could not find a file URL" in none
    for c in (ok, big, dead, none):
        assert TERMS in c and "Not email." in c
        assert "written by a person, not by this bot" in c   # never poses as the review
    # 300 exactly is inside the limit, 301 is not — the boundary the money turns on
    assert "inside the 300-line limit" in compose(body, 200, 300, now)
    assert "over the 300-line limit" in compose(body, 200, 301, now)
    print("selftest ok — 4 branches, the 300/301 boundary, and no branch claims to be the review")


def main():
    body = os.environ.get("ISSUE_BODY", "")
    url = field(body, "Public URL of the file")
    status, lines = fetch(url) if url else (None, None)
    print(compose(body, status, lines, datetime.now(timezone.utc)))


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()
