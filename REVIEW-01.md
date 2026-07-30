# Code review: `scripts/nettop.py`

**Zitacron Inc. — one-file review, sample**

The column labelled `PER-SEC` is not a per-second rate. It is the raw counter delta over a
0.5-second sampling window, never divided by that window, so every throughput figure nettop prints
understates the real rate by a factor of about two. Two further defects stop the tool dead: it
raises an unhandled `KeyError` the moment a network interface appears while it is running, and an
unhandled `curses.error` on any terminal too short for the interfaces present — four interfaces on
a standard 80x24 terminal is enough.

| | |
|---|---|
| File | `https://raw.githubusercontent.com/giampaolo/psutil/master/scripts/nettop.py` |
| Project | giampaolo/psutil |
| Licence | BSD 3-Clause |
| Length | 160 lines |
| Scope | Every line read, then each quoted line re-checked byte-for-byte against its cited line number. Two supporting files (`psutil/_common.py`, `scripts/top.py`) were read to confirm claims made about them. |

---

## 1. `PER-SEC` under-reports throughput by a factor of about two — high

**Line 103**

```python
                stats_after.bytes_sent - stats_before.bytes_sent) + '/s',
```

`poll()` sleeps for `interval` (line 70) and `main()` sets `interval = 0.5` (line 152) for every
iteration after the first. The value printed under the `PER-SEC` heading (line 98) is the plain
difference between the two samples — bytes moved in roughly half a second — and it is never divided
by `interval` before the `/s` suffix is appended. The same omission repeats at line 109 for
`bytes-recv` and at lines 114 and 119 for the two packet counters.

**Consequence.** A link genuinely running at 100 MB/s is displayed at about 50 MB/s. The error is
silent, consistent and plausible-looking, which is the worst combination for a diagnostic tool: the
number is wrong in the direction that makes you stop investigating. Anyone using nettop to judge
whether a link is saturated concludes it has twice the headroom it really has. Separately, the
first frame runs with `interval = 0` (line 146), so its `PER-SEC` column is the delta across two
adjacent syscalls — effectively zero, and meaningless.

**Fix.** Divide by the sampling window. Change line 103 to:

```python
                (stats_after.bytes_sent - stats_before.bytes_sent) / interval) + '/s',
```

with the same change at line 109. The two packet rows need `round()` so they keep printing
integers rather than `24.0`:

```python
            round((stats_after.packets_sent - stats_before.packets_sent) / interval),
```

`interval` must reach `refresh_window`: add it to the signature at line 76 and pass it at line 151
(`refresh_window(*args, interval)`). To avoid dividing by zero on the first pass, delete
`interval = 0` at line 146 and `interval = 0.5` at line 152, and initialise `interval = 0.5` once
before the `while` loop. The first frame then costs an extra half second and shows a real rate
instead of a fabricated zero.

---

## 2. Crashes with `KeyError` when an interface appears mid-window — medium

**Line 94**

```python
        stats_before = pnic_before[name]
```

`nic_names` is built from the keys of `pnic_after` (line 91), the sample taken *after* the sleep,
but is then used to index `pnic_before`, taken 0.5 seconds *before* it. Any interface that comes
into existence inside that window is present in one dictionary and absent from the other. The loop
spends nearly all of its wall time inside that sleep, so an interface appearing at any point during
a run will almost certainly land in a window rather than between them.

**Consequence.** Bringing up a VPN, starting a Docker container, attaching a `veth` pair, plugging
in USB tethering or connecting to Wi-Fi while nettop is running raises `KeyError: '<ifname>'`.
`main()` catches only `KeyboardInterrupt` and `SystemExit` (line 153), so the tool exits with a
traceback. This is a monitoring tool, and a new interface is precisely the event during which you
would be watching it.

**Fix.** Treat a newly seen interface as having a zero delta for its first window:

```python
        stats_before = pnic_before.get(name, pnic_after[name])
```

---

## 3. Crashes with `curses.error` when output exceeds the terminal height — medium

**Line 153**

```python
    except (KeyboardInterrupt, SystemExit):
```

`printl` resets `lineno` and re-raises on `curses.error` (line 60), which implies callers are meant
to handle it. Its twin in `scripts/top.py` does exactly that — the identical helper is called there
inside `try: printl(line) / except curses.error: break`. No caller in this file does, and the
handler in `main()` does not list it.

Each interface emits six lines (a highlighted header, four counter rows and a blank spacer) and the
totals block adds two, so a frame occupies `2 + 6N` rows for `N` interfaces. On an 80x24 terminal
that overflows at four interfaces (26 rows). Four is unremarkable: loopback, a wired NIC, Wi-Fi and
any one of `docker0`, `virbr0`, `tailscale0` or a VPN tunnel.

**Consequence.** `python3 scripts/nettop.py` aborts on the first frame with an
`addwstr() returned ERR` traceback on any host whose interface count exceeds the window height, and
a running session dies if the window is resized smaller. The terminal itself is restored correctly
by the `finally` block, so the damage is limited to the tool exiting.

**Fix.** The sort at line 92 already puts the busiest interfaces first, so truncating to what fits
discards the least useful data. Insert after line 92:

```python
    nic_names = nic_names[: max(0, (win.getmaxyx()[0] - 2) // 6)]
```

Alternatively, wrap each `printl` call in `try/except curses.error: break`, matching the pattern
already proven in `scripts/top.py`.

---

## Dropped

Reported findings are limited to what the file demonstrably does. Five candidates were examined and
discarded:

- **Line 92, `sum(pnic_after[x])` as a sort key** adds byte counts, packet counts and error/drop
  counts together — three different units. In practice byte counts dominate by several orders of
  magnitude, so the resulting order is the one the comment on line 88 intends. Untidy, not a defect.
- **Line 67, `tot_before` is computed, returned and passed to `refresh_window` but never used**
  (only `tot_after` is read, lines 83-84). One redundant syscall per frame and a dead parameter. No
  effect on output.
- **Docstring lines 15-16 advertise a `total packets:` row** that `refresh_window` never prints.
  Documentation drift, cosmetic.
- **Counter wraparound producing negative deltas.** Real in principle, but 64-bit counters make it
  vanishingly rare on the platforms psutil targets, and `bytes2human` handles a negative input
  through `abs()` and returns `-4.9K` rather than raising. Not worth a buyer's attention.
- **A supporting argument for finding 1 was withdrawn during verification.** An earlier draft cited
  the `0.00 B/s` figures in the module docstring as evidence of the zero-length first window.
  `bytes2human` as currently defined returns `0.0B`, so that sample output predates the present
  code and proves nothing. Finding 1 rests on the arithmetic at lines 103-119 alone.

---

**What this file does well.** The two-sample `poll()` / `refresh_window()` split is the right shape
for a rate monitor — sampling is isolated from rendering, both counter reads happen a known distance
apart, and the whole tool is legible in one screen with no state beyond a line counter. The
arithmetic bug in finding 1 is one operator away from correct precisely because the structure around
it is sound.

---

This is a sample of the paid service: **CA$5 per file, 300 lines maximum**, at most three findings, each citing a line, refunded if late or if there is nothing worth saying.

**[Buy a CA$5 slot →](https://buy.stripe.com/4gM3cu5WPac12jugwFbEA00)** · [Request a review](https://github.com/zitacron/zitacron-code-review/issues/new?template=review-request.yml) · [Terms](TERMS.md)
