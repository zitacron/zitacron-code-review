#!/usr/bin/env python3
"""check_short_tip_script.py
QA gate for .autopilot/SHORT_TIP_SCRIPT.md (product #542, signal #476).
Asserts the template:
  - contains the tip link (bEA03), not the slot link as primary
  - does not put the slot link (bEA02) before the tip link
  - names the repo URL
  - contains a CLOSING LINE section
  - explicitly says what NOT to do (no sell-the-slot as first ask)
  - tip link appears before slot link in the file
Exit 0 = all pass. Exit 1 = one or more failures.
"""
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / "SHORT_TIP_SCRIPT.md"

TIP_LINK  = "buy.stripe.com/3cI14m70Tck9f6ga8hbEA03"
SLOT_LINK = "buy.stripe.com/aFadR84SLesh9LWa8hbEA02"
REPO_URL  = "github.com/zitacron/zitacron-code-review"

failures = []

def check(label, cond):
    if cond:
        print(f"  PASS {label}")
    else:
        print(f"  FAIL {label}")
        failures.append(label)

text = SCRIPT.read_text()
lower = text.lower()

check("script file exists and is non-empty", len(text) > 200)
check("tip link present (bEA03)",  TIP_LINK in text)
check("slot link present (bEA02)", SLOT_LINK in text)
check("repo URL present",          REPO_URL in text)
check("CLOSING LINE section present", "## CLOSING LINE" in text)
check("WHAT NOT TO DO section present", "## WHAT NOT TO DO" in text)
check("tip link appears before slot link",
      text.index(TIP_LINK) < text.index(SLOT_LINK))
check("no bare bEA02 in DESCRIPTION block before bEA03",
      text.find(SLOT_LINK) > text.find(TIP_LINK))
check("CA$3 minimum mentioned", "CA$3" in text)
check("'buys nothing' stated", "buys nothing" in text)

print()
if failures:
    print(f"FAILED: {len(failures)} of {len(failures)+text.count('PASS')} — {failures}")
    sys.exit(1)
else:
    print(f"ALL PASS ({10} assertions)")
