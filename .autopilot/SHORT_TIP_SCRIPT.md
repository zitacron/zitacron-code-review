# Show-the-work Short — description template and closing script
# Product: zcr-short-tip-ask (product #542, signal #476)
#
# USE: paste the DESCRIPTION block as the YouTube Short description.
# Read or paraphrase the CLOSING LINE at the end of the recording.
# Do NOT use the CA$2 slot CTA as the primary ask on a show-the-work Short —
# that is what Short #57 did and it added 1 view over two weeks while #58
# (show-the-work, no tip ask) added 5. The tip follows value that landed.

---

## DESCRIPTION (paste verbatim, edit only the bracketed fields)

[FINDING HEADLINE — one sentence, e.g. "This function silently returns the wrong
rate on its first call"]

I read [FILENAME] from [PROJECT] — a real public file, not a demo.
Full written review: github.com/zitacron/zitacron-code-review

If that was useful: tip what it was worth →
https://buy.stripe.com/3cI14m70Tck9f6ga8hbEA03
CA$3 minimum. You choose the amount. It buys nothing.

Want your own file read? CA$2, 300 lines max, delivery via GitHub issue.
github.com/zitacron/zitacron-code-review

---

## CLOSING LINE (say at the end of the recording, after showing the fix)

"If that saved you time, there's a tip link in the description — you pick the
amount, CA$3 minimum, and it buys nothing. Full written review is on GitHub."

---

## WHAT NOT TO DO

- Do not end the video with "CA$2 code review available" as the first ask.
  That is the sell-the-slot format. Put the tip first; slot second.
- Do not add the checkout link buy.stripe.com/aFadR84SLesh9LWa8hbEA02 to the
  description. That is the slot link, not the tip link.
- Do not post the description to any channel you do not own.

---

## LINKS (verified)

Tip link (CA$3 floor):  https://buy.stripe.com/3cI14m70Tck9f6ga8hbEA03
Slot link (CA$2):       https://buy.stripe.com/aFadR84SLesh9LWa8hbEA02  [secondary only]
Repo:                   https://github.com/zitacron/zitacron-code-review
Issue template:         https://github.com/zitacron/zitacron-code-review/issues/new?template=review-request.yml

---

## MEASURE AFTER 14 DAYS

Record baseline views before posting (youtube_views.py).
After 14 days compare:
  - Short #57 (sell-the-slot): ~44 views, ~0 likes
  - Short #58 (show-the-work, no tip ask): ~38 views, 2 likes
  - This Short (show-the-work + tip ask): ?

Also check: any tip events in check_stripe_payments.py output (bEA03 link).

If views < #58 AND tips = 0 after 14 days: format is the constraint, not the ask.
File that as a kill signal on signal #476, not a copy problem.
