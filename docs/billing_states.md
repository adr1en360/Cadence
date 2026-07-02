# Billing State Machine

## Six Subscription States

```mermaid
stateDiagram-v2
    [*] --> trialing: merchant creates subscription with trial
    [*] --> active: merchant creates subscription (no trial)
    
    trialing --> active: trial ends + first payment succeeds
    trialing --> cancelled: merchant or subscriber cancels during trial
    
    active --> past_due: renewal payment fails
    active --> cancelled: subscriber cancels (end of period)
    active --> expired: plan reaches end date
    
    past_due --> active: retry payment succeeds
    past_due --> suspended: all retry attempts exhausted (3 retries)
    
    suspended --> active: subscriber updates payment method + charge succeeds
    suspended --> cancelled: merchant cancels
    
    cancelled --> [*]
    expired --> [*]
```

## State Definitions

| State | Meaning | Access | Dunning Active? |
|-------|---------|--------|-----------------|
| `trialing` | Free trial period, no charge yet | Full access | No |
| `active` | Paid and current | Full access | No |
| `past_due` | Renewal failed, retrying | Full access (grace) | **Yes** |
| `suspended` | All retries exhausted | **No access** | No |
| `cancelled` | Ended by merchant or subscriber | No access | No |
| `expired` | Plan reached its end date | No access | No |

## Dunning Schedule (past_due state)

| Retry | Delay After Failure | Action on Fail | Action on Success |
|-------|-------------------|----------------|-------------------|
| 1st | 1 day | Stay `past_due`, schedule retry 2 | → `active` |
| 2nd | 3 days after retry 1 | Stay `past_due`, schedule retry 3 | → `active` |
| 3rd | 7 days after retry 2 | → `suspended` | → `active` |

Total grace period: **11 days** from first failure to suspension.

## Transition Rules (Enforced in Code)

```python
VALID_TRANSITIONS = {
    "trialing":  ["active", "cancelled"],
    "active":    ["past_due", "cancelled", "expired", "suspended"],
    "past_due":  ["active", "suspended"],
    "suspended": ["active", "cancelled"],
    "cancelled": [],   # terminal
    "expired":   [],   # terminal
}
```

## Events Generated

Every transition creates an `Event` record:

| Trigger | Event Type | Example |
|---------|-----------|---------|
| First payment succeeds | `subscription.status_updated` | Trial → Active |
| Renewal payment fails | `payment.failed` | Active → Past Due |
| Retry succeeds | `payment.succeeded` | Past Due → Active |
| All retries exhausted | `subscription.status_updated` | Past Due → Suspended |
| Subscriber cancels | `subscription.cancelled` | Active → Cancelled |
| Card updated + charged | `subscription.status_updated` | Suspended → Active |

---

## Pre-Flight Verification & Recovery (Dual-Write Protection)

To prevent double-charging a customer if a network timeout or local database crash occurs immediately after a successful charge but before the database transaction is committed:
1. Before every charge attempt, the engine queries the database for any existing `pending` payment record generated in the current cycle.
2. If found, the engine executes a pre-flight query to Nomba's requery API (`verify_transaction`).
3. If Nomba confirms the payment succeeded downstream, Cadence bypasses executing a new charge, advances the subscription's `period_end` dates locally, and completes the state synchronization securely.

_Last updated: 2026-07-02_
