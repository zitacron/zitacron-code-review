#!/usr/bin/env bash
# Post every review added under reviews/ to the issue thread it is named for.
#
# TERMS clause 2: "Delivery is by a comment on a public issue in the offer repository, and that
# is what counts as delivered." So the delivery step is a comment, and a comment is something a
# human can forget to post while the 24-hour clock runs. This removes that failure mode: write
# reviews/<issue-number>.md, push, and the buyer has it.
#
#   .github/deliver.sh <before-sha> <after-sha>   # post what changed between them
#   .github/deliver.sh --selftest                 # filename rules, no network
#
# Needs GH_TOKEN and REPO in the environment. Never invents an issue number: a file that is not
# reviews/<digits>.md is skipped loudly, because guessing which stranger's thread a review
# belongs on is worse than not delivering it.
set -euo pipefail

EMPTY_SHA=0000000000000000000000000000000000000000

# The one piece of real logic here, so it is the piece with a test.
issue_number() {
    local base
    base="$(basename "$1" .md)"
    case "$base" in
        '' | *[!0-9]*) return 1 ;;
        *) printf '%s' "$base" ;;
    esac
}

selftest() {
    local ok
    for good in reviews/1.md reviews/42.md reviews/007.md; do
        issue_number "$good" >/dev/null || { echo "FAIL: $good rejected"; exit 1; }
    done
    for bad in reviews/README.md reviews/12-draft.md reviews/notes.md reviews/.md reviews/12a.md; do
        ok=0
        issue_number "$bad" >/dev/null 2>&1 || ok=1
        [ "$ok" = 1 ] || { echo "FAIL: $bad accepted as an issue number"; exit 1; }
    done
    [ "$(issue_number reviews/42.md)" = "42" ] || { echo "FAIL: wrong number"; exit 1; }
    echo "selftest ok — only reviews/<digits>.md delivers; README and drafts are skipped"
}

[ "${1:-}" = "--selftest" ] && { selftest; exit 0; }

before="${1:?before sha}"
after="${2:?after sha}"
# First push to a branch reports an all-zero "before"; fall back to the single commit.
if [ "$before" = "$EMPTY_SHA" ] || [ -z "$before" ]; then
    before="$(git rev-parse "${after}^" 2>/dev/null || printf '%s' "$after")"
fi

# Added or modified only — a deleted review must not be re-posted.
git diff --name-only --diff-filter=AM "$before" "$after" -- 'reviews/*.md' | while read -r f; do
    if ! n="$(issue_number "$f")"; then
        echo "skip $f — not reviews/<issue-number>.md"
        continue
    fi
    gh issue comment "$n" --repo "$REPO" --body-file "$f"
    echo "delivered $f -> issue #$n"
done
