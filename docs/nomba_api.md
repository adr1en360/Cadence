# Nomba API Reference — Cadence Integration

> Everything we know about the Nomba APIs from docs + sandbox testing.

## Credentials

All credentials are loaded from environment variables (`.env` file, gitignored). See `.env.example` for the full list.

| Env Var | Description |
|---------|-------------|
| `NOMBA_ACCOUNT_ID` | Parent (main) account ID — used in `accountId` header |
| `NOMBA_SUB_ACCOUNT_ID` | Sub-account ID — scope API calls to this account |
| `NOMBA_CLIENT_ID` | OAuth2 client ID |
| `NOMBA_CLIENT_SECRET` | OAuth2 client secret (private key) |

> **Never commit real values.** Use `.env` locally, Render env vars in production.

## Base URLs

| Environment | Base URL | Checkout Path Prefix |
|-------------|----------|---------------------|
| Sandbox | `https://sandbox.nomba.com` | `/sandbox/checkout/` |
| Production | `https://api.nomba.com` | `/v1/checkout/` |

Config flag `NOMBA_ENV=sandbox|production` switches all paths.

---

## 1. Authentication (OAuth2)

**Endpoint:** `POST /v1/auth/token/issue`

```json
// Request
{
  "grant_type": "client_credentials",
  "client_id": "<NOMBA_CLIENT_ID>",
  "client_secret": "<NOMBA_CLIENT_SECRET>"
}
// Headers: accountId: <NOMBA_ACCOUNT_ID>
```

```json
// Response
{
  "code": "00",
  "data": {
    "access_token": "eyJhbGci...",
    "refresh_token": "01h4gdx2...",
    "expiresAt": "2026-01-01T12:00:00Z"
  }
}
```

**Critical:** Token expires in **30 minutes**. Cadence must cache per-merchant and refresh proactively.

**Refresh:** `POST /v1/auth/token/refresh` (use before expiry, not after)

---

## 2. Create Checkout Order

**Sandbox:** `POST /sandbox/checkout/order`
**Production:** `POST /v1/checkout/order`
**Headers:** `Authorization: Bearer <token>`, `accountId: <account_id>`

```json
// Request
{
  "order": {
    "orderReference": "cadence_sub_001",
    "amount": "2000.00",
    "currency": "NGN",
    "customerEmail": "student@example.com",
    "callbackUrl": "https://cadence.onrender.com/webhooks/nomba"
  },
  "tokenizeCard": true,
  "allowedPaymentMethods": ["Card"]
}
```

```json
// Response
{
  "code": "00",
  "data": {
    "checkoutLink": "https://pay.nomba.com/sandbox/<encrypted-ref>",
    "orderReference": "cadence_sub_001"
  }
}
```

**Key:** `tokenizeCard: true` tells Nomba to save the card and return a `tokenKey` for future charges.

---

## 3. Tokenized Card Payment (Recurring Charges)

**Endpoint:** `POST /v1/checkout/tokenized-card-payment`
**Headers:** `Authorization: Bearer <token>`, `accountId: <account_id>`, `X-Idempotent-key: <unique-key>`

```json
// Request
{
  "order": {
    "orderReference": "cadence_renewal_001",
    "customerId": "762878332454",
    "callbackUrl": "https://cadence.onrender.com/webhooks/nomba",
    "customerEmail": "student@example.com",
    "amount": "2000.00",
    "currency": "NGN"
  },
  "tokenKey": "7628788443"
}
```

**Critical:** `X-Idempotent-key` header prevents duplicate charges. Casing matters.

---

## 4. List Tokenized Cards

**Endpoint:** `GET /v1/checkout/tokenized-card-data?customerEmail=<email>`
**Headers:** `Authorization: Bearer <token>`, `accountId: <account_id>`

```json
// Response
{
  "data": {
    "tokenizedCardDataList": [
      {
        "tokenKey": "e890bd1a9f0d",
        "customerEmail": "student@example.com",
        "cardType": "Mastercard",
        "cardPan": "543462****2808",
        "tokenExpirationDate": "12/30"
      }
    ]
  }
}
```

**Alternative to webhook for getting tokenKey.** Query by `customerEmail` after successful first payment.

---

## 5. Checkout Refund

**Sandbox:** `POST /sandbox/checkout/refund`
**Production:** `POST /v1/checkout/refund`

```json
{
  "transactionId": "WEB-ONLINE_C-abc123-550e4c3a-...",
  "amount": 2000.00
}
```

---

## 6. Fetch Transaction (Verify)

**Sandbox:** `GET /sandbox/checkout/transaction?idType=orderReference&id=<ref>`
**Production:** `GET /v1/checkout/transaction?idType=orderReference&id=<ref>`

---

## 7. Webhooks

### Event Types
- `payment_success` — charge completed
- `payment_failed` — charge failed
- `payout_success` — transfer completed
- `payout_refund` — refund completed

### Signature Headers
| Header | Value |
|--------|-------|
| `nomba-signature` | HMAC-SHA256 signature (Base64) |
| `nomba-sig-value` | Raw signature value |
| `nomba-signature-algorithm` | Always `HmacSHA256` |
| `nomba-timestamp` | ISO 8601 UTC timestamp |

### HMAC Signing Recipe
**NOT raw body.** Structured colon-delimited string:

```
{event_type}:{requestId}:{userId}:{walletId}:{transactionId}:{type}:{time}:{responseCode}:{nomba-timestamp}
```

Then: `HMAC-SHA256(secret_key, signing_string)` → Base64 encode → compare with `nomba-signature` header.

### Sample Webhook Payload (Card Payment Success)
```json
{
  "event_type": "payment_success",
  "requestId": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "merchant": { "userId": "<accountId>" },
    "tokenKey": "e890bd1a9f0d",
    "transaction": {
      "fee": 0.28,
      "type": "online_checkout",
      "transactionId": "WEB-ONLINE_C-abc123-...",
      "transactionAmount": 2000.00,
      "time": "2026-06-30T10:00:00Z"
    },
    "order": {
      "amount": 2000.00,
      "orderId": "a1b2c3d4-...",
      "orderReference": "cadence_sub_001",
      "paymentMethod": "card_payment",
      "currency": "NGN"
    }
  }
}
```

### Where tokenKey comes from
1. **Primary:** `payment_success` webhook payload at `data.tokenKey` (see sample above). The webhook fires synchronously in sandbox — capture `tokenKey` here to avoid an extra API call.
2. **Fallback:** `GET /v1/checkout/tokenized-card-data?customerEmail=<email>` — poll only if `tokenKey` is missing from the webhook payload.

---

## Sandbox Test Cards

| Card Number | Outcome | Next Step |
|-------------|---------|-----------|
| `5434621074252808` | OTP required | Submit OTP `9999` → success |
| `4000000000002503` | 3DS required | Handle 3DS redirect |
| `5484497218317651` | Declined | Payment fails (dunning test) |

**PIN:** `1234` (not validated in sandbox)
**CVV/Expiry:** Any values accepted

### OTP Values
| OTP | Outcome |
|-----|---------|
| `9999` | Approved |
| `1234` | Timeout |
| `5464` | Invalid OTP |

---

## Gotchas (Learned the Hard Way)

1. **Cloudflare blocks Python urllib** — must set browser User-Agent header
2. **No-auth mode uses different paths** — `POST /v1/checkout/order` (no auth) vs `POST /sandbox/checkout/order` (auth required)
3. **Sandbox webhook = synchronous** — fires immediately after OTP, but no-auth mode may not fire webhooks at all
4. **Tokenized cards in sandbox = hardcoded mock data** — `tokenKey` is a mock value, but the field path is real
5. **Orders expire in 48 hours** in sandbox (Redis-backed)
6. **Transaction ID format:** `WEB-ONLINE_C-{first6charsOfAccountId}-{UUID}`

_Last updated: 2026-07-01_
