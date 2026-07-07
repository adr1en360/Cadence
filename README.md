# Cadence

[![Hackathon](https://img.shields.io/badge/Hackathon-DevCareer%20%C3%97%20Nomba%202026-blueviolet)](https://github.com/adr1en360/Cadence)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**Cadence** is a managed subscription billing engine built on top of Nomba's online payment APIs. It provides Nigerian developers with the recurring billing infrastructure they otherwise have to build from scratch.

By sitting as an orchestration layer between your software application and Nomba's payment primitives, Cadence automatically handles tokenized card authorizations, billing periods, automatic retries (dunning logic), and webhook states on your behalf.

---

## The Problem & The Solution

### The Problem
Nigerian developers building subscription-based products have no managed billing infrastructure available locally. Stripe Billing does not operate here, and building recurring billing on raw payment APIs requires writing extensive infrastructure (a state machine, a retry scheduler, and verification checks) before writing a single line of actual product. The result is that most SaaS builders handle renewals manually, which does not scale and loses revenue to failed payments.

### The Solution
Cadence sits as a service layer between Nomba and your backend. A merchant creates a plan, enrolls a customer via a single API call, and redirects them to the checkout page. Once the card is tokenized, Cadence handles all future charges, retries, and state transitions automatically. 

Your backend simply listens to webhook events to grant or revoke access. Neither the merchant nor the subscriber ever touches Nomba's raw APIs directly.

---

## Lifecycle Flow

```mermaid
sequenceDiagram
    autonumber
    actor Subscriber
    participant MerchantApp as Merchant App
    participant Cadence
    participant Nomba as Nomba API

    Note over Subscriber, Nomba: Phase 1: Checkout & Tokenization
    MerchantApp->>Cadence: POST /api/subscriptions (plan_id, email)
    Cadence->>Nomba: Create Checkout Order (tokenizeCard=true)
    Nomba-->>Cadence: Checkout Link
    Cadence-->>MerchantApp: Checkout Link
    MerchantApp-->>Subscriber: Redirect to Nomba Checkout page
    Subscriber->>Nomba: Enters card details & submits OTP
    Nomba->>Cadence: Webhook: payment_success (with tokenKey)
    Cadence->>Cadence: Store tokenKey, transition to Active
    Cadence->>MerchantApp: Webhook: subscription.status_updated

    Note over Subscriber, Nomba: Phase 2: Automated Renewals & Dunning
    Note over Cadence: Dunning Scheduler Cron Runs
    alt Subscription is Active & Renewal is Due
        Cadence->>Nomba: Charge tokenKey (with X-Idempotent-key)
        alt Charge Succeeds
            Nomba-->>Cadence: Success status
            Cadence->>MerchantApp: Webhook: payment.succeeded
        else Charge Fails
            Nomba-->>Cadence: Failed status
            Cadence->>Cadence: Move to past_due, schedule retry
            Cadence->>MerchantApp: Webhook: payment.failed
        end
    end
```

---

## Core Features

- **7-State Billing Machine:** Enforces a rigid, validated state transition lifecycle (`pending_payment`, `trialing`, `active`, `past_due`, `suspended`, `cancelled`, `expired`).
- **Automated Dunning:** Automatically retries failed charges on an escalating schedule (Day 1, Day 3, Day 7) before suspending access.
- **Double-Charge Protection:** Intercepts retry schedules and queries Nomba's transaction verification API to verify any pending payment before executing a new charge, preventing double-billing during network or database timeouts.
- **Hosted Self-Service Portal:** Provides subscribers a passwordless, token-secured portal to view billing history, update cards, or change plans.
- **Multi-Tenancy:** Isolation scoped at the Project level. API keys, plans, and subscribers are restricted to their authorized merchant projects.

---

## Installation & Local Setup

### Prerequisites
*   Python 3.10+
*   [uv](https://github.com/astral-sh/uv) (Astral's fast Python package manager)
*   Docker (for running the local database)

### 1. Clone the Repository
```bash
git clone https://github.com/adr1en360/Cadence.git
cd Cadence
```

### 2. Set Up Virtual Environment & Dependencies
Create a virtual environment and install requirements using `uv`:
```bash
uv venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

uv pip install -r requirements.txt
```

### 3. Start Local Database (Docker)
Start the PostgreSQL instance locally using Docker:
```bash
docker run -d --name cadence-db \
  -e POSTGRES_USER=cadence \
  -e POSTGRES_PASSWORD=cadence123 \
  -e POSTGRES_DB=cadence \
  -p 5432:5432 \
  postgres:16-alpine
```

### 4. Configure Environment Variables
Copy the example environment file and configure your credentials:
```bash
cp .env.example .env
```
Open `.env` and fill in your **Nomba Sandbox Credentials**:
- `NOMBA_CLIENT_ID`
- `NOMBA_CLIENT_SECRET`
- `NOMBA_ACCOUNT_ID`

---

## Running the Application

### Start Development Server
```bash
uv run uvicorn app.main:app --reload --port 8000
```
- **Merchant Dashboard:** Open [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to manage projects, plans, and subscribers.
- **Developer Documentation Portal:** Open [http://localhost:8000/developer](http://localhost:8000/developer) to view public API references and webhook guides.

### Running the Dunning Scheduler
The dunning scheduler is decoupled from the main web server process and should be run independently via a cron job (e.g. Render Cron Job):
```bash
uv run python scripts/run_dunning.py
```

---

## Developer Quickstart & Integration

For complete integration details, see [docs/developer_flow.md](docs/developer_flow.md).

### 1. Create a Plan
```bash
curl -X POST https://cadence-p0x6.onrender.com/api/plans \
  -H "Authorization: Bearer cd_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Pro Monthly",
    "amount": 2000.00,
    "currency": "NGN",
    "interval_days": 30,
    "trial_days": 0
  }'
```

### 2. Enroll a Subscriber
Call this endpoint to create a subscription and get the redirect checkout link:
```bash
curl -X POST https://cadence-p0x6.onrender.com/api/subscriptions \
  -H "Authorization: Bearer cd_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_abc123",
    "customer_email": "customer@example.com",
    "customer_name": "Tunde Balogun",
    "callback_url": "https://your-app.com/checkout/success"
  }'
```

### 3. Handle Webhook Events
Cadence signs all outgoing webhook payloads with your project's Webhook Secret using HMAC-SHA256. Verify signatures in your webhook route:

```python
import hmac
import hashlib

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## Configuration Reference

The following environment variables configure the service:

| Variable | Description | Default |
|----------|-------------|---------|
| `NOMBA_ENV` | Nomba environment (`sandbox` or `production`) | `sandbox` |
| `NOMBA_ACCOUNT_ID` | Parent (main) account ID | |
| `NOMBA_CLIENT_ID` | Nomba OAuth2 Client ID | |
| `NOMBA_CLIENT_SECRET` | Nomba OAuth2 Client Secret | |
| `NOMBA_WEBHOOK_SECRET` | Signature key for verifying incoming Nomba webhooks | |
| `DATABASE_URL` | SQLAlchemy connection URL for PostgreSQL | |
| `SECRET_KEY` | Secret key for JWT signing & cookies | |
| `JWT_ALGORITHM` | Algorithm for JWT tokens | `HS256` |
| `PORT` | Local server port | `8000` |
| `BASE_URL` | Public URL of the Cadence deployment | `http://localhost:8000` |

---

## Development & Testing

### Running Tests
To run unit and integration tests:
```bash
uv run pytest
```

### Test Scripts Reference
- **Verify local DB connection:**
  ```bash
  uv run python tests/test_db_connection.py
  ```
- **Verify Nomba authentication:**
  ```bash
  uv run python tests/test_nomba_auth.py
  ```
- **Assert core integration flows (seeding, checkout, transitions):**
  ```bash
  uv run python tests/test_core_services.py
  ```

---

## Documentation Index

- [docs/developer_flow.md](docs/developer_flow.md) — End-to-end integration walkthrough
- [docs/api_surface.md](docs/api_surface.md) — REST API endpoints reference
- [docs/billing_states.md](docs/billing_states.md) — 7-state lifecycle transition rules
- [docs/nomba_api.md](docs/nomba_api.md) — Inbound Nomba webhooks signature receipt
- [docs/nomba_sandbox_cards.md](docs/nomba_sandbox_cards.md) — Test card details and PIN/OTP triggers

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
