# Cadence

[![Hackathon](https://img.shields.io/badge/Hackathon-DevCareer%20%C3%97%20Nomba%202026-blueviolet)](https://github.com/adr1en360/Cadence)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Cadence** is a managed subscription billing engine built on Nomba's payment APIs. It gives Nigerian developers automated recurring billing infrastructure they'd otherwise have to build from scratch.

By sitting as an orchestration layer between your application and Nomba's payment primitives, Cadence handles the subscription lifecycle, payment schedules, automatic retry logic (dunning), and subscription state transitions on your behalf.

---

## Why Cadence?

Building subscription billing locally in Nigeria is challenging because Stripe Billing does not operate here, and building recurring billing on raw payment APIs requires writing extensive infrastructure before writing product code.

Cadence solves this by automating:
*   **Automatic Renewals:** Charges stored tokenized cards automatically when a renewal is due using Nomba's Tokenized Card Payment API.
*   **Failed Payment Recovery (Dunning):** Automatically retries failed payments on an escalating schedule (1 day, 3 days, 7 days) before suspending access.
*   **Subscription State Machine:** Enforces a rigid lifecycle across six subscription states (`trialing`, `active`, `past_due`, `suspended`, `cancelled`, `expired`).
*   **Tenant Scoping:** Full multi-tenant dashboard and developer API access scopes every operation to the authorized merchant.
*   **Self-Service Customer Portal:** Provides subscribers a passwordless, token-secured portal to view billing history, update cards, or cancel.

---

## Architecture Overview

```
                        +----------------------------------------+
                        |           Merchant App                 |
                        +--------------------+-------------------+
                                             | REST API / Webhooks
                                             v
                        +--------------------+-------------------+
                        |             Cadence                    |
                        |   +--------------------------------+   |
                        |   |        FastAPI Engine          |   |
                        |   +---------------+----------------+   |
                        |                   |                    |
                        |                   v                    |
                        |   +--------------------------------+   |
                        |   |  Dunning Scheduler (Thread)    |   |
                        |   +---------------+----------------+   |
                        +-------------------|--------------------+
                                            | Nomba API (HTTPS)
                                            v
                        +--------------------+-------------------+
                        |            Nomba APIs                  |
                        +----------------------------------------+
```

For a detailed look at system architecture and subscription rules, see:
*   [docs/billing_states.md](docs/billing_states.md) — Subscription State Machine & Dunning Rules
*   [docs/nomba_api.md](docs/nomba_api.md) — Nomba API Integration & Webhook Signatures

---

## Installation & Setup

### Prerequisites
*   Python 3.10+
*   [uv](https://github.com/astral-sh/uv) (Astral's fast Python package manager)
*   Docker (for running the local database)

### 1. Clone the Repository
```bash
git clone https://github.com/adr1en360/Cadence.git
cd Cadence
```

### 2. Set Up Virtual Environment
Create a virtual environment using `uv`:
```bash
uv venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
Install all requirements using `uv`:
```bash
uv pip install -r requirements.txt
```

### 4. Start Local Database (Docker)
Start the PostgreSQL instance locally using Docker:
```bash
docker run -d --name cadence-db \
  -e POSTGRES_USER=cadence \
  -e POSTGRES_PASSWORD=cadence123 \
  -e POSTGRES_DB=cadence \
  -p 5432:5432 \
  postgres:16-alpine
```

### 5. Configure Environment Variables
Copy the example environment file and configure your credentials:
```bash
copy .env.example .env
```
Open `.env` and fill in your **Nomba Test Credentials**:
*   `NOMBA_CLIENT_ID`
*   `NOMBA_CLIENT_SECRET`
*   `NOMBA_ACCOUNT_ID`
*   `NOMBA_SUB_ACCOUNT_ID`

---

## Run the Application

Start the local development server:
```bash
uv run uvicorn app.main:app --reload --port 8000
```
FastAPI will start the web app and initialize the background dunning scheduler thread automatically.
*   **Merchant Dashboard:** Open `http://localhost:8000/dashboard`
*   **Interactive API Docs:** Open `http://localhost:8000/docs`

---

## Configuration Reference

The following environment variables configure the service:

| Variable | Description | Default |
|----------|-------------|---------|
| `NOMBA_ENV` | Nomba environment (`sandbox` or `production`) | `sandbox` |
| `NOMBA_ACCOUNT_ID` | Parent (main) account ID | |
| `NOMBA_SUB_ACCOUNT_ID`| Sub-account ID for scoping transactions | |
| `NOMBA_CLIENT_ID` | Nomba OAuth2 Client ID | |
| `NOMBA_CLIENT_SECRET` | Nomba OAuth2 Client Secret (Private Key) | |
| `DATABASE_URL` | SQLAlchemy connection string for PostgreSQL | |
| `SECRET_KEY` | Secret key for JWT signing & cookies | |
| `JWT_ALGORITHM` | Algorithm for JWT tokens | `HS256` |
| `PORT` | Local server port | `8000` |

---

## Development & Testing

### Running Tests
To run unit and integration tests (ensure your test DB is configured):
```bash
uv run pytest
```

### Testing Checkout & Webhooks Locally
1. Run ngrok to expose your port:
   ```bash
   ngrok http 8000
   ```
2. Trigger a checkout order using the helper script:
   ```bash
   uv run scripts/create_checkout.py <your_ngrok_url>
   ```
3. Complete the checkout payment using the test cards in [docs/nomba_api.md](docs/nomba_api.md).

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
