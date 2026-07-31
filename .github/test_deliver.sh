#!/usr/bin/env bash
# End-to-end test for deliver.sh, with no network and no GitHub: a scratch repo and a fake `gh`
# that records what it was asked to post.
#
#   .github/test_deliver.sh
#
# deliver.sh --selftest covers the filename rule. This covers the part that decides whether a
# buyer gets their review once and only once: which files a given pair of commits delivers.
set -euo pipefail

ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/bin"
cat > "$WORK/bin/gh" <<'FAKE'
#!/usr/bin/env bash
# stands in for: gh issue comment <n> --repo R --body-file F
n="$3"; body=""
while [ $# -gt 0 ]; do [ "$1" = "--body-file" ] && body="$2"; shift; done
printf '%s|%s\n' "$n" "$(cat "$body")" >> "$CALLS"
FAKE
chmod +x "$WORK/bin/gh"
export PATH="$WORK/bin:$PATH" CALLS="$WORK/calls" GH_TOKEN=fake REPO=zitacron/zitacron-code-review
: > "$CALLS"

cd "$WORK"
git init -q . && git config user.email t@t && git config user.name t
mkdir -p .github reviews
cp "$ROOT/.github/deliver.sh" .github/
git add -A && git commit -qm base
BASE="$(git rev-parse HEAD)"

fail() { echo "FAIL: $1"; exit 1; }

# 1. a review reaches the thread it is named for, and nothing else does
printf 'three findings, line 103\n' > reviews/42.md
printf 'not a review\n' > reviews/README.md
git add -A && git commit -qm r42
bash .github/deliver.sh "$BASE" HEAD > out1 2>&1
grep -q 'delivered reviews/42.md -> issue #42' out1 || fail "42 not delivered: $(cat out1)"
grep -q 'skip reviews/README.md' out1 || fail "README not skipped"
[ "$(wc -l < "$CALLS")" = 1 ] || fail "expected 1 gh call, got: $(cat "$CALLS")"
grep -qx '42|three findings, line 103' "$CALLS" || fail "wrong thread or body: $(cat "$CALLS")"

# 2. an unrelated commit re-posts nothing — no buyer gets the same review twice
PREV="$(git rev-parse HEAD)"
printf 'x\n' > README.md && git add -A && git commit -qm docs
: > "$CALLS"
bash .github/deliver.sh "$PREV" HEAD > /dev/null 2>&1
[ ! -s "$CALLS" ] || fail "re-posted an unchanged review: $(cat "$CALLS")"

# 3. a withdrawn review is not re-posted
PREV="$(git rev-parse HEAD)"
git rm -q reviews/42.md && git commit -qm rm
: > "$CALLS"
bash .github/deliver.sh "$PREV" HEAD > /dev/null 2>&1
[ ! -s "$CALLS" ] || fail "posted a deleted review: $(cat "$CALLS")"

# 4. the all-zero "before" GitHub sends on a first push still delivers
printf 'first push review\n' > reviews/7.md
git add -A && git commit -qm r7
: > "$CALLS"
bash .github/deliver.sh 0000000000000000000000000000000000000000 HEAD > out4 2>&1
grep -qx '7|first push review' "$CALLS" || fail "zero-sha fallback broke: $(cat out4)"

echo "e2e ok — right thread, right body, once; README, deleted and unchanged post nothing; zero-sha handled"
