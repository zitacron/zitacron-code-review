# Code review — `vercel/async-retry`, `lib/index.js`

**Zitacron Inc. — one-file review, sample**

A callback that rejects with `undefined` or `null` takes down the whole process: line 26 dereferences `err.bail` with no null check, and on the asynchronous path that `TypeError` is thrown inside a `.catch()` callback whose promise is discarded, so on default Node it terminates the process with an error that names the wrong cause, and in any process that installs an `unhandledRejection` handler the promise returned by `retry()` simply never settles. Separately, `bail()` does not stop retrying — it only rejects the outer promise, so an aborted operation keeps firing attempts and repeating their side effects against a promise that has already settled.

| | |
|---|---|
| **File** | [`lib/index.js`](https://raw.githubusercontent.com/vercel/async-retry/main/lib/index.js) — 61 lines |
| **Repository** | [vercel/async-retry](https://github.com/vercel/async-retry) v1.3.3 |
| **Commit reviewed** | `2b1d3fe` (2020-01-02) |
| **Licence** | MIT |
| **Findings** | 3 reported, 4 dropped |

All three findings were confirmed by executing a verbatim copy of the source against `retry@0.13.1` on Node v22.22.3, not by reading alone. Each proposed fix was applied to that copy and re-run.

---

## 1. A nullish rejection kills the process, or hangs the promise forever — line 26

**Severity: high.** The trigger is narrow — the rejected value must be `null` or `undefined`. The outcome when it triggers is not narrow, and no correct error reaches the caller either way.

```js
26      if (err.bail) {
```

`err` is dereferenced with no null check. When the retried callback rejects with a nullish value — `Promise.reject()` with no argument, `throw null`, or a dependency that rejects with a non-value — this line throws `TypeError: Cannot read properties of undefined (reading 'bail')`.

On the asynchronous path, that throw happens inside `catchIt`:

```js
48      Promise.resolve(val)
49        .then(resolve)
50        .catch(function catchIt(err) {
51          onError(err, num);
52        });
```

The promise returned by `.catch(...)` is neither returned nor awaited. `resolve` and `reject` are therefore never called, and the `TypeError` escapes as an unhandled rejection.

**Consequence.** Two outcomes, both measured:

- **Default Node (15 and later).** The unhandled rejection terminates the process. It exits with code `1` and prints the `TypeError` stack pointing at line 26 — an error that describes async-retry's internals, not the failure the caller actually needs to see. The original rejection is gone.
- **Any process with an `unhandledRejection` handler installed** — routine in servers, and the norm under most logging and process-supervision setups — **and in browsers.** The rejection is swallowed and the promise returned by `retry()` never settles. `await retry(...)` blocks permanently: no rejection, no timeout, no retry. A request handler leaks one pending promise per call, and the caller's own timeout is the only thing that ever fires.

In both cases the operation is attempted exactly once; the retry behaviour the library exists to provide never happens.

The synchronous-throw path at line 43 fails differently: that `TypeError` escapes the promise executor, so the caller does get a rejection, but it is the wrong error and it buries the original failure.

**Fix.** Normalise the value before touching it. Insert before line 26:

```js
      if (err == null) {
        err = new Error('async-retry: callback rejected with ' + err);
      }

      if (err.bail) {
```

Verified: with `retries: 2` the callback is now attempted three times and the promise rejects normally. Note that a bare `if (err && err.bail)` is not sufficient — it stops the hang, but `op.retry(undefined)` then returns `false` and line 32 rejects with `null`, which is barely an improvement.

---

## 2. `bail()` does not stop retrying — line 22

**Severity: medium**

```js
22      reject(err || new Error('Aborted'));
```

That line is the whole of `bail`. The README describes it as "a `Function` you can invoke to abort the retrying", but rejecting a promise cancels nothing. `bail` records no state, and neither `onError` (line 25) nor `runAttempt` (line 38) checks whether a bail has occurred.

So if the callback continues past `bail(...)` and then throws, `onError` takes the normal path, `op.retry(err)` schedules another attempt, and the callback runs again against an already-settled promise.

**Consequence.** With `retries: 3`, a callback that calls `bail(new Error('unauthorized'))` and then throws executes **four times** — measured, not inferred. Every side effect in that callback repeats: POSTs, charges, writes, rate-limit consumption. The errors from those extra attempts are unreportable, because the promise rejected on the first one. The README example sidesteps this by writing `return;` on the line after `bail`, but nothing in the code enforces that, and it does not help when the code between `bail` and the `return` is what throws.

**Fix.** Record the bail and short-circuit. Lines 21-23 become:

```js
    var bailed = false;

    function bail(err) {
      bailed = true;
      reject(err || new Error('Aborted'));
    }
```

and line 26 becomes `if (bailed || err.bail) {`. Verified: the same test case drops from four invocations to one, still rejecting with `unauthorized`.

---

## 3. The caller's options object is mutated — line 11

**Severity: low**

```js
 6      var options = opts || {};
11        options.randomize = true;
```

Line 6 aliases the caller's object rather than copying it, so the write on line 11 lands on the object the caller passed in.

**Consequence.** Two failure modes, both reproduced. A shared or reused options object silently acquires `randomize: true` after the first `retry()` call, so any later consumer of that object inherits jitter it never configured. And because this is a sloppy-mode CommonJS module, passing `Object.freeze({ retries: 3 })` makes the assignment fail *silently* rather than throw — `randomize` stays undefined, `node-retry` falls back to its own default of `false` (confirmed: timeouts come back as `[100, 100, 100]`, no jitter), and the default of `randomize: true` documented in the README quietly does not apply.

**Fix.** Copy instead of alias. Line 6 becomes:

```js
    var options = Object.assign({}, opts);
```

`Object.assign({}, undefined)` returns `{}`, so the omitted-`opts` case that `|| {}` was covering still works — verified, along with the frozen-options case.

---

## Dropped

We report only what we can stand behind. Four candidates were investigated and discarded:

- **`onRetry` fires after `op.retry()` (lines 31-34).** Looks like an ordering slip. It is not: the README states `onRetry` is "invoked after a new retry is performed", and `op.retry` only *schedules* the attempt, so the callback still runs before it.
- **`reject(op.mainError())` (line 32).** `mainError()` returns the most *frequent* error, not the last — a run that fails once with a 500 and twice with a connection reset rejects with the reset. Surprising, but that is `node-retry`'s documented semantic and this file uses the API correctly.
- **No overall deadline option.** A missing feature, not a defect; the caller can wrap the promise.
- **`var` and non-arrow callbacks throughout.** Deliberate — the repo's eslint config explicitly disables `no-var` and `prefer-arrow-callback`.

---

**What this file does well:** the try/catch around `fn(bail, num)` at lines 41-46 combined with `Promise.resolve(val)` at line 48 means a callback that throws synchronously, returns a plain value, or returns a promise are all retried identically — precisely the part hand-rolled retry helpers usually get wrong.

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
