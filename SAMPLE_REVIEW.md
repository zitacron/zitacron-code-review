# Sample review

Example input:

```python
def reserve(stock, quantity):
    if stock >= quantity:
        stock -= quantity
    return True
```

## Findings

1. **Incorrect success result:** the function returns `True` when stock is
   insufficient. Return a failure result on that branch.
2. **Discarded state change:** subtracting from the local integer does not
   update the caller's stock. Return the new value or update owned state.
3. **Invalid quantities:** zero and negative values are accepted; a negative
   value increases stock. Require a positive quantity before comparison.

One possible correction:

```python
def reserve(stock, quantity):
    if quantity <= 0 or quantity > stock:
        return False, stock
    return True, stock - quantity
```

An actual review cites the submitted file and its surrounding repository
context rather than reviewing an isolated toy example.
