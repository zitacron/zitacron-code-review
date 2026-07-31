# reviews/

One file per delivered review, named for the issue thread it belongs to:
`reviews/<issue-number>.md`.

Pushing one to `main` posts it as a comment on that issue automatically
(`.github/workflows/deliver.yml`), which is what TERMS clause 2 counts as delivery. Write the
review, push, done — there is no separate "remember to paste it" step for the 24-hour clock to
run out against.

This README is deliberately not named after a number, so the workflow skips it. Anything that
is not `reviews/<digits>.md` is skipped rather than guessed at.
