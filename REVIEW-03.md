## One-file code review — `bin/git-force-clone`

**Zitacron Inc.** · sample review · single-file, fixed price

| | |
|---|---|
| Repository | [tj/git-extras](https://github.com/tj/git-extras) |
| File | [`bin/git-force-clone`](https://raw.githubusercontent.com/tj/git-extras/master/bin/git-force-clone) (as of commit `e793f89`, the most recent commit to touch this file) |
| Licence | MIT |
| Length | 109 lines |
| Verified against | git 2.43.0, GNU bash 5.2.21, GNU grep 3.11, local bare remote |

---

When the destination repository already exists — the entire reason this command exists — `git-force-clone` exits successfully only if there is exactly one stale local branch. With two or more, line 97 hands the whole branch list to `git branch -D` as a single quoted argument, so git reports `error: branch 'stale-one stale-two' not found` and every stale branch survives, contrary to the script's own help text; with none at all, line 95 aborts the run under `set -e` after all the real work has already succeeded.

Both behaviours were reproduced against a local bare remote, not inferred from reading. A control run confirms the boundary precisely: zero stale branches exits 1, one exits 0, two exits 1.

---

### 1. Line 97 — quoted list passed to `git branch -D` deletes nothing (high)

```bash
        git branch -D "${branches}"
```

`branches` is a space-separated string built by `xargs` on line 95. Quoting it collapses the list into a single argument, so git looks for one branch literally named `stale-one stale-two`.

**Consequence.** With two or more stale local branches, none is deleted and the subshell aborts. The documented contract — *"local branches and other remotes will be removed"* — does not hold. The working tree itself is fine, because lines 90-91 have already checked out and hard-reset it; what survives is exactly the local state the command promised to destroy, and the command reports failure while doing so. Observed: `error: branch 'stale-one stale-two' not found`, exit 1, both branches still listed by `git branch`.

**Minimal fix.** Split deliberately:

```bash
        # shellcheck disable=SC2086
        git branch -D ${branches}
```

Sturdier, and it removes the `xargs` round-trip entirely (safe here because line 90 always reattaches HEAD to `${branch}` first):

```bash
      mapfile -t branches < <(git branch --format='%(refname:short)' | grep -Fxv "${branch}")
      if [ ${#branches[@]} -gt 0 ]; then
        git branch -D "${branches[@]}"
      fi
```

Both forms were applied and re-tested against zero, one and two stale branches, plus the fresh-clone and default no-`-b` paths.

---

### 2. Line 95 — `grep` with no match aborts the script under `set -euo pipefail` (medium)

```bash
      branches=$(git branch | grep -v '*' | xargs)
```

When the current branch is the only local branch, `grep -v` matches nothing and exits 1. `set -o pipefail` propagates that status to the pipeline — `xargs` itself exits 0 — and an assignment whose command substitution fails is itself a failing simple command, so `set -e` kills the subshell before the `-n` guard on line 96 is ever reached.

**Consequence.** In the common case of a repository with a single local branch, the script performs every operation correctly (remotes reset, branch checked out, tree hard-reset) and then exits 1 with no diagnostic. Any CI step, Makefile, or wrapper that checks the exit status reads a clean force-clone as a failure. Rated medium rather than high because the repository is left in the correct state: the cost is a false failure signal and the retries or aborted builds that follow it, not damaged data. Observed: exit status 1, correct final state, empty error output.

**Minimal fix.**

```bash
      branches=$(git branch | grep -v '*' | xargs) || true
```

The existing `if [ -n "${branches}" ]` on line 96 is then the sole piece of control flow, which is clearly what was intended.

---

### 3. Line 55 — `-b` as the last argument exits silently (low)

```bash
    shift
```

The option loop shifts twice for `-b`: once on line 43, once here. If `-b` is the final argument, the second `shift` runs with no positional parameters left, returns non-zero, and trips `set -e`.

**Consequence.** `git force-clone -b` exits 1 printing nothing at all — no error, no usage — bypassing the `_check` helper that exists to report exactly this. By contrast, running the command with no arguments correctly prints `Error: Missing remote_url` plus the usage block. A user who forgets the branch name gets silence. Observed: exit 1, stdout and stderr both empty.

**Minimal fix.**

```bash
    shift || break
```

Execution then falls through to the existing `_check` calls and prints `Error: Missing remote_url`. Validating where the value is read is clearer still, and yields a precise message — inserting `_check "${2:-}" "branch name after ${1}"` immediately above line 42 produces `Error: Missing branch name after -b`. Both variants were tested and leave normal invocations unaffected.

---

### Dropped

We report only what we can stand behind, so the following were considered and set aside:

- **Line 79, `grep -oP`.** The PCRE lookbehind is GNU-specific, and a failure there would abort the default (no `-b`) path under `pipefail`. git-extras ships through Homebrew, so a macOS portability problem is plausible — but we have no macOS machine to test on, and an unverified claim does not belong in a paid review. Noted, not billed.
- **Line 94, `# shellcheck disable=SC2063`.** Not a defect. A leading `*` is literal in a POSIX basic regular expression, and git rejects `*` in branch names (confirmed: `fatal: 'star*name' is not a valid branch name`), so the filter is correct and the suppression is honest.
- **Line 64, `[ -d "${destination_path}/.git" ]`.** Misses linked worktrees and submodules, where `.git` is a file rather than a directory; the script then falls through to `git clone` into a non-empty directory and fails. Real but narrow — worth a passing mention, not a finding. `git -C "${destination_path}" rev-parse --git-dir` covers both forms.
- **Line 69, unquoted `$(git remote)`.** Word splitting is deliberate here and git remote names cannot contain whitespace. Style, not a bug.

---

### What this file does well

It is disciplined where it matters: `set -euo pipefail` from line 3, positional parameters read defensively as `${1:-}` and `${2:-}` so a missing argument never trips `set -u`, all destructive work confined to a subshell so the caller's working directory is never changed, and a `--help` block that states plainly that the command destroys local work before it does so.

---

Nobody paid for this review. We picked a public file, read it properly, and published what we
found — unasked, and to the same standard as the paid ones.

If it was worth something to you: **[tip what it was worth
→](https://buy.stripe.com/3cI14m70Tck9f6ga8hbEA03)** — you choose the amount, CA$3 minimum. It
buys nothing, gets you nothing, and creates no obligation in either direction. [Why CA$3, and
what a tip is not](TIP.md).

Want your own file read? **CA$2 per file**, 300 lines maximum, at most three findings each
citing a line, refunded if late or if there is nothing worth saying. Delivery is a comment on a
public issue in this repository — that is the only channel, because this org has no outbound
email and will not promise you something it cannot send.

**[Buy a CA$2 slot →](https://buy.stripe.com/aFadR84SLesh9LWa8hbEA02)** · [Request a
review](https://github.com/zitacron/zitacron-code-review/issues/new?template=review-request.yml)
· [Terms](TERMS.md)
