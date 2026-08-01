## One-file code review — `libexec/pyenv-latest`

**Zitacron Inc.** · sample review · single-file, fixed price

| | |
|---|---|
| Repository | [pyenv/pyenv](https://github.com/pyenv/pyenv) (master at `f5915fc`) |
| File | [`libexec/pyenv-latest`](https://raw.githubusercontent.com/pyenv/pyenv/master/libexec/pyenv-latest) (as of commit `6481d14`, the most recent commit to touch this file) |
| Licence | MIT |
| Length | 105 lines |
| Verified against | GNU bash 5.2.21, GNU coreutils `sort` 9.4, GNU sed, mawk / nawk / busybox awk, and the complete python-build definition list — 1,433 definitions read from the repository tree at `f5915fc` |

---

`pyenv latest` does not return the latest version. For 12 of the 69 prefixes we swept it returns an
older build than one it can see, because the sort key it builds hides the `-` separator from
`sort -n`: `pyenv latest --known pypy2.7` answers `pypy2.7-5.10.0`, a 2017 release, while
`pypy2.7-7.3.22` sits in the same candidate list. CPython is unaffected — every `3.x` prefix we
tried is correct — so this lands entirely on PyPy, Miniconda, Anaconda and Miniforge users.

Two smaller defects sit alongside it: the free-threaded `t` marker is stripped from the value the
script hands back on every failure path, so `pyenv prefix 3.13t` reports `version '3.13' not
installed` — a version the user never typed — and `pyenv latest` with no argument at all answers
with an empty string and exit 0.

Every claim below was reproduced by running this file, not inferred from reading it. Where a fix is
given it was applied and re-tested, including against the cases that must not change.

---

### 1. Lines 76-89 — the sort key hides `-` from `sort -n`, so the newest build loses (high)

```bash
          | sort -t. -k1,1r -k 2,2nr -k 3,3nr -k4,4nr \
```

Line 80-84 composes a sort key by inserting a `.` after the leading `impl-` run, then line 87 sorts
it with `.` as the field separator and `-n` on fields 2 to 4. Version strings, however, use *two*
separators. Every `-` that is not the one awk replaced stays inside a field, and `sort -n` stops
reading at it — so the number after that `-` never takes part in the comparison at all.

The two `pypy2.7` candidates, with the keys this file gives them:

```
pypy2.7-7.3.22...|pypy2.7-7.3.22     f1=pypy2  f2=7-7   f3=3    f4=22
pypy2.7-5.10.0...|pypy2.7-5.10.0     f1=pypy2  f2=7-5   f3=10   f4=0
```

`f2` is `7-7` against `7-5`; under `-n` both read as 7, so PyPy 7.x versus 5.x is never compared.
The decision falls to `f3`, which compares 7.3.22's `3` against 5.10.0's `10` — and 10 wins.

**Consequence.** `pyenv install <prefix>` resolves through this file
(`plugins/python-build/bin/pyenv-install` line 198, `pyenv-latest -f -k`), so the wrong answer is
what gets built. Observed against the real definition list, current output first:

| prefix | `pyenv latest -k` returns | newest matching definition |
|---|---|---|
| `pypy2.7` | `pypy2.7-5.10.0` | `pypy2.7-7.3.22` |
| `pypy3.5` | `pypy3.5-5.10.1` | `pypy3.5-7.0.0` |
| `miniconda3-3.9` | `miniconda3-3.9-4.12.0` | `miniconda3-3.9-25.9.1-3` |
| `miniconda3-3.12` | `miniconda3-3.12-24.11.1-0` | `miniconda3-3.12-26.5.3-1` |
| `anaconda3` | `anaconda3-2025.12-1` | `anaconda3-2025.12-2` |
| `miniforge3` | `miniforge3-26.3.2-0` | `miniforge3-26.3.2-3` |

The same root cause produces both magnitudes. Where the swallowed `-` separates two version
components (`pypy2.7-7.3.22`, `miniconda3-3.9-25.9.1-3`) the result is years out of date; where it
separates only a build number (`anaconda3-2025.12-1` against `-2`) the keys tie outright and
`sort`'s last-resort whole-line comparison — which is ascending, `-r` having been given per-key —
picks the *lowest* build number.

**Minimal fix.** Make `-` a separator in the key rather than something buried in a field. Replace
the `awk` at lines 77-84 with:

```bash
    DEFINITION_CANDIDATES=(\
        $(printf '%s\n' "${DEFINITION_CANDIDATES[@]}" | \
          awk '{ key = $0; gsub(/-/, ".", key); print key "........|" $0 }'))
```

and give line 87 enough numeric keys to reach the end of that key:

```bash
          | sort -t. -k1,1r -k2,2nr -k3,3nr -k4,4nr -k5,5nr -k6,6nr -k7,7nr -k8,8nr \
```

Eight, because the deepest key in the current definition list is `miniconda3-3.9-25.9.1-3` →
`miniconda3.3.9.25.9.1.3`, seven fields; the padding must be at least as long as the key count so
that `|<original>` never lands inside a compared field. Sweeping all 69 prefixes, this changes
exactly the 12 wrong answers — each to a later release of the same distribution — and leaves the
other 57 byte-identical, CPython included. It also retires the `match`/`substr` pair entirely.

**What we tried first, and why it is not the fix.** Replacing the whole key-and-sort block with
`sort -Vr` looks like the obvious repair and is worse. It changes 16 answers; 8 agree with the fix
above and the other 8 are wrong, because a version sort ranks a differently-named variant, or a
different numbering series, above the plain distribution:

```
graalpy          graalpy-25.0.3             ->  graalpy-community-25.0.3
pypy             pypy-5.7.1                 ->  pypy-stm-2.5.1
miniconda3-3.9   miniconda3-3.9-4.12.0      ->  miniconda3-3.9.1
```

`pypy-stm-2.5.1` is not merely a different flavour — 2.5.1 is older than the 5.7.1 it displaces —
and `miniconda3-3.9.1` is an old Miniconda release, not the Python 3.9 series the prefix names.
Worth stating plainly: `sort -V` cannot be used to check this file's output either, for the same
reason. The comparisons above are against the definition list read directly.

---

### 2. Lines 57-60 — the free-threaded `t` is dropped from the version the script reports (medium)

```bash
    if [[ $prefix =~ ^(.*[0-9])t$ ]]; then
        suffix="t"
        prefix="${BASH_REMATCH[1]}"
    fi
```

Stripping `t` off `prefix` is right for matching — line 68 puts it back as `suffix_re`. But
`prefix` is also what lines 96 and 98 report when nothing matches, and by then the `t` is gone.

**Consequence.** The header comment documents `-b/--bypass` as *"do not print an error message but
rather print the argument unchanged"*. It does not print the argument unchanged. Observed with
`3.13.0` and `3.13.1` installed and no free-threaded build present:

```
pyenv latest 3.13t       ->  pyenv: no installed versions match the prefix `3.13'   exit 1
pyenv latest -b 3.13t    ->  3.13                                                   exit 1
pyenv latest -f 3.13t    ->  3.13                                                   exit 0
```

`libexec/pyenv-prefix` line 48 takes that value with `-f`, which always exits 0, and line 54 puts it
straight into its own message. Running the real `pyenv-prefix` against that tree:

```
pyenv prefix 3.13t  ->  pyenv: version `3.13' not installed
```

The user asked for a free-threaded 3.13 and is told a version they never named is missing. Rated
medium, not high: nothing is installed or deleted wrongly, and the resolution itself is correct
whenever a free-threaded build *is* present (`3.13t` → `3.13.1t`, confirmed). The cost is a
diagnostic that sends the reader after the wrong thing.

**Minimal fix.** Keep the argument as typed and report that:

```bash
prefix=$1
requested=$1     # as typed: messages and -b/-f must echo this, not $prefix
```

then use `$requested` in the message on line 96 and in the `echo` on line 98. Re-tested: the three
lines above become `` `3.13t' ``, `3.13t`, `3.13t`, exit codes unchanged, and `3.13`, `3.13t` and
`3` all still resolve exactly as before.

---

### 3. Lines 41-45 — no argument at all is answered with an empty string and success (low)

```bash
        if [[ -d $PYENV_ROOT/versions/$prefix ]]; then
            echo "$prefix"
            exit $exitcode;
        fi
```

With no argument, `prefix` is empty, the test becomes `-d $PYENV_ROOT/versions/` — which is true on
any working pyenv — and the script echoes the empty string and exits 0. Usage on line 3 marks
`<prefix>` as required, and the `--known` path still rejects it properly (`no known versions match
the prefix ''`, exit 1), so the two halves of the same command now disagree.

**Consequence.** A caller doing `v=$(pyenv latest "$requested")` with an empty `requested` reads
success and an empty version instead of an error. This is a regression, not long-standing
behaviour: it arrived with the exact-match fast path in `6481d14`. Deleting those four lines
restores the prior response, which we confirmed:

```
before 6481d14  ->  pyenv: no installed versions match the prefix `'   exit 1
current         ->  (nothing)                                          exit 0
```

**Minimal fix.** Reject it where the argument is read, in the form the rest of `libexec/` already
uses (`pyenv-whence` line 33, `pyenv-hooks` line 20, `pyenv-version-file-write` line 28):

```bash
if [[ -z $prefix ]]; then
    pyenv-help --usage latest >&2
    exit 1
fi
```

Tested: prints `Usage: pyenv latest [-k|--known] <prefix>` and exits 1, with every non-empty prefix
unaffected.

---

### Dropped

We report only what we can stand behind, so the following were considered and set aside:

- **Line 81, `substr($0, 0, RLENGTH-1)`.** awk strings are 1-indexed, so a start index of 0 is out
  of range and a strict reading returns one character fewer than intended. We could not make it
  misbehave: mawk, nawk and busybox awk all return the intended `graalpy`. gawk is not installed on
  this machine and we do not report untested claims. It is moot in any case — every candidate
  reaching that line shares the user's prefix, so a uniform truncation cannot reorder them, and the
  fix in finding 1 removes the call.
- **Line 73, the conditional `sed` argument.** `IFS=$'\n'` is in force from line 39, so
  `$(... echo "-e /[0-9]t\$/d")` is not split on its space and arrives as a single argument with a
  leading blank in the script. GNU sed tolerates it and the filter works. BSD sed is the open
  question — pyenv ships through Homebrew — and we have no macOS machine to test on. Noted, not
  billed.
- **Line 39, `IFS=$'\n'` with no `set -f`.** The unquoted command substitutions on lines 46, 48, 67,
  71, 78 and 86 are still subject to pathname expansion, so a version whose name contains a glob
  character could be rewritten against the current directory. Worth noting because `libexec/pyenv-prefix`
  line 33 sets `set -f` for exactly this reason, with a comment explaining it — but it needs a
  deliberately hostile directory name to bite, so it is a consistency point, not a finding.
- **Line 42, the fast path and `--skip-envs`.** It accepts any directory under
  `$PYENV_ROOT/versions`, including the pyenv-virtualenv environments that the `--skip-envs` on line
  46 exists to exclude. For `pyenv prefix` and `pyenv version-name` resolving a virtualenv name is
  arguably what you want, and we cannot test the plugin here. Mentioned, not billed.

---

### What this file does well

The prefix matching is more careful than it first looks. Line 68 requires a `-` or `.` immediately
after the prefix, so `pyenv latest 3.1` correctly declines to match `3.10.0` — a boundary most
hand-rolled prefix matchers get wrong. Lines 63-64 quote the user's input into a regex character by
character rather than trusting it, with the source of the technique cited in a comment. The
`-b`/`-f` options are marked internal in the header and explain themselves, and line 65 carries an
honest `FIXME` about the very pipeline that turned out to hold finding 1.

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
