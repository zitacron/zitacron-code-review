# Sample review

This is the format you receive: up to three findings, each with a severity, the line it
sits on, why it matters, and what to do about it.

## Example input

`inventory.py`, lines 1–4:

```python
def reserve(stock, quantity):
    if stock >= quantity:
        stock -= quantity
    return True
```

## Findings

### 1. Reports success on the failure path — high

**Line 4.** `return True` sits outside the `if`, so a caller trying to reserve more than
exists is told the reservation succeeded. Any caller branching on this result takes the
wrong branch, and it fails silently — no exception, no log, just an overcommitted stock
count that surfaces later as a shortage nobody can trace.

Return a failure result on the path where the guard does not hold.

### 2. The decrement is discarded — high

**Line 3.** `stock -= quantity` rebinds the local parameter. Integers are immutable and
arrive by value, so the caller's stock is untouched. The function reports a reservation
it did not make — the same end state as finding 1, reached by a different route, which is
why fixing only one of the two leaves the bug alive.

Return the new value, or move the decrement onto state the function actually owns.

### 3. Non-positive quantities are accepted — medium

**Line 2.** `stock >= quantity` holds for zero and for negative quantities. A negative
quantity passes the guard and then *increases* stock at line 3 — a reserve call that
manufactures inventory. Require a positive quantity before the comparison.

## One possible correction

```python
def reserve(stock, quantity):
    if quantity <= 0 or quantity > stock:
        return False, stock
    return True, stock - quantity
```

Note this changes the signature: the function returned a bare `bool` and now returns
`(bool, int)`. Every existing caller breaks, and callers written as `if reserve(...)`
break *silently*, because a non-empty tuple is always truthy — they will read as success
on every call, including refusals. Ship it behind a new name or a deprecation shim if the
function is public. A review that hands you this fix without mentioning the change has
left you a worse bug than the one it closed.

---

A real review cites your submitted file and the surrounding repository context rather
than an isolated toy example.
