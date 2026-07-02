# Cadence Public API Surface

> The endpoints a merchant developer calls to integrate Cadence into their application.
> All routes are tenant-scoped — every request is authenticated and bound to a single merchant via API key.

## Base URL

| Environment | Base URL |
|-------------|----------|
| Local dev | `http://localhost:8000` |
| Production | `https://cadence.onrender.com` |

## Authentication

All developer API routes require a Cadence API key in the `Authorization` header:

```
Authorization: Bearer cd_<prefix>_<secret>
```

Merchants generate API keys from the dashboard (`/dashboard`) or via the auth endpoints after logging in with JWT.

---

## Plans

Plans define billing products — a price, currency, interval, and optional trial period. A merchant must create at least one plan before creating subscriptions.

### `POST /api/plans` — Create Plan

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✓ | Human-readable plan name |
| `amount` | float | ✓ | Charge amount per interval (must be > 0) |
| `currency` | string | | ISO 4217 code, 3 chars. Default: `NGN` |
| `interval_days` | int | ✓ | Billing cycle length in days (must be > 0) |
| `trial_days` | int | | Free trial period in days. Default: `0` |

**Response:** `201 Created`
```json
{
  "id": "plan_abc123",
  "name": "Pro Monthly",
  "amount": 5000.0,
  "currency": "NGN",
  "interval_days": 30,
  "trial_days": 7,
  "is_active": true
}
```

### `GET /api/plans` — List Plans

Returns all active plans for the authenticated merchant.

**Response:** `200 OK` — Array of plan objects.

### `GET /api/plans/{plan_id}` — Get Plan

Returns a single plan by ID (must belong to authenticated merchant).

**Response:** `200 OK` — Plan object.  
**Error:** `404 Not Found` — Plan not found or does not belong to merchant.

### `DELETE /api/plans/{plan_id}` — Delete Plan

Soft-deletes (deactivates) a plan. Existing subscriptions on this plan are not affected.

**Response:** `204 No Content`  
**Error:** `404 Not Found`

---

## Subscriptions

Subscriptions bind a customer to a plan. Creating a subscription initiates a Nomba checkout flow — the customer must complete payment before the subscription activates.

### `POST /api/subscriptions` — Create Subscription

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plan_id` | string | ✓ | ID of an active plan owned by the merchant |
| `customer_email` | string (email) | ✓ | Subscriber's email |
| `customer_name` | string | | Subscriber's display name |
| `callback_url` | string (URL) | ✓ | Where to redirect after the customer completes checkout |

**Response:** `201 Created`
```json
{
  "id": "sub_xyz789",
  "plan_id": "plan_abc123",
  "customer_email": "student@example.com",
  "customer_name": "Adrien",
  "status": "trialing",
  "current_period_start": "2026-07-01T00:00:00",
  "current_period_end": "2026-07-08T00:00:00",
  "checkout_link": "https://pay.nomba.com/sandbox/<encrypted-ref>"
}
```

> [!IMPORTANT]
> The response includes a `checkout_link`. Redirect the customer to this URL to complete initial card payment and tokenization. The subscription remains inactive until Nomba confirms payment via webhook.

**Error:** `404 Not Found` — Plan does not exist or does not belong to merchant.

### `GET /api/subscriptions` — List Subscriptions

Returns all subscriptions for the authenticated merchant.

**Response:** `200 OK` — Array of subscription summary objects.

### `GET /api/subscriptions/{sub_id}` — Get Subscription

Returns full subscription details including billing state, retry count, and token status.

**Response:** `200 OK`
```json
{
  "id": "sub_xyz789",
  "plan_id": "plan_abc123",
  "customer_email": "student@example.com",
  "customer_name": "Adrien",
  "status": "active",
  "current_period_start": "2026-07-01T00:00:00",
  "current_period_end": "2026-07-31T00:00:00",
  "token_key": "e890bd1a9f0d",
  "retry_count": 0,
  "next_retry_at": null,
  "cancelled_at": null,
  "created_at": "2026-07-01T00:00:00",
  "updated_at": "2026-07-01T12:00:00",
  "cancel_at_period_end": false
}
```

**Error:** `404 Not Found`

### `POST /api/subscriptions/{sub_id}/cancel` — Cancel Subscription

Cancels the subscription. By default, this immediately terminates the subscription and transitions status to `cancelled`. You can optionally schedule the cancellation for the end of the current billing cycle by providing a JSON body.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cancel_at_period_end` | boolean | | If true, the subscription remains active until the end of the billing period, then cancels automatically. Default: false. |

**Response:** `200 OK`
```json
{
  "message": "Subscription scheduled to cancel at period end",
  "status": "active",
  "cancel_at_period_end": true
}
```

**Error:** `400 Bad Request` — Invalid state transition.  
**Error:** `404 Not Found`

---

## Customer Portal

The portal is a subscriber-facing UI (not a JSON API). Merchants generate portal URLs and give them to their customers.

### `POST /api/subscriptions/{sub_id}/portal-link` — Generate Portal Link

> [!NOTE]
> This endpoint allows merchants to programmatically generate time-limited, token-secured portal URLs for their subscribers.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| *(none)* | — | — | Subscription ID in the path is sufficient |

**Response:** `200 OK`
```json
{
  "portal_url": "https://cadence.onrender.com/portal/sub_xyz789?token=<short-lived-token>",
  "expires_at": "2026-07-01T18:00:00Z"
}
```

### Current Portal Routes (Subscriber-Facing, Token-Protected)

These routes serve HTML pages and are accessed directly by the subscriber via the portal link:

| Route | Method | Description |
|-------|--------|-------------|
| `/portal/{sub_id}` | GET | Portal UI — view billing, card status, cancel |
| `/api/portal/{sub_id}/update-card` | POST | Initiate card re-tokenization (returns `checkout_link`) |
| `/api/portal/{sub_id}/cancel` | POST | Cancel subscription from the portal |

> [!NOTE]
> Portal routes are authenticated via a short-lived token (`token` query parameter) generated by the `portal-link` endpoint, which is validated against the subscription's `portal_token` and `portal_token_expires_at` database columns.

---

## Webhooks (Cadence → Merchant)

Cadence will forward billing events to merchant-configured webhook URLs. This is planned functionality.

### Planned Event Types

| Event | Fires When |
|-------|------------|
| `subscription.status_updated` | Subscription status changes (trialing, active, past_due, suspended, expired) |
| `subscription.cancelled` | Subscription cancelled by merchant or subscriber |
| `payment.succeeded` | Any successful charge (initial, renewal, or retry) |
| `payment.failed` | Any failed charge attempt |
| `payment.refunded` | Any payment refund |

See [billing_states.md](billing_states.md) for the complete state machine and event definitions.

---

## Webhooks (Nomba → Cadence)

These are internal — Nomba sends payment events to Cadence at:

```
POST /webhooks/nomba
```

This is **not** a developer-facing endpoint. Merchants do not call or configure this URL. It is hardcoded as the `callbackUrl` in Nomba checkout orders.

---

## Error Format

All error responses follow this shape:

```json
{
  "detail": "Human-readable error message"
}
```

Standard HTTP status codes:
- `400` — Bad request / invalid state transition
- `401` — Missing or invalid API key
- `404` — Resource not found or not owned by merchant
- `500` — Internal server error (Nomba call failed, etc.)

---

## Route Summary

| Method | Path | Auth | Category |
|--------|------|------|----------|
| `POST` | `/api/plans` | API Key | Plans |
| `GET` | `/api/plans` | API Key | Plans |
| `GET` | `/api/plans/{plan_id}` | API Key | Plans |
| `DELETE` | `/api/plans/{plan_id}` | API Key | Plans |
| `POST` | `/api/subscriptions` | API Key | Subscriptions |
| `GET` | `/api/subscriptions` | API Key | Subscriptions |
| `GET` | `/api/subscriptions/{sub_id}` | API Key | Subscriptions |
| `POST` | `/api/subscriptions/{sub_id}/cancel` | API Key | Subscriptions |
| `POST` | `/api/subscriptions/{sub_id}/portal-link` | API Key | Portal *(planned)* |
| `GET` | `/portal/{sub_id}` | Portal Token | Portal UI |
| `POST` | `/api/portal/{sub_id}/update-card` | Portal Token | Portal |
| `POST` | `/api/portal/{sub_id}/cancel` | Portal Token | Portal |

_Last updated: 2026-07-01_
