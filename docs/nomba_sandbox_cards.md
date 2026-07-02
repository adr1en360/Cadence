# Nomba Sandbox Test Card Reference

Use these test card details and inputs to simulate different transaction results and verify your Cadence integration end-to-end.

## Sandbox Base URL
*   **Sandbox API Endpoint:** `https://sandbox.nomba.com`
*   **Checkout URL Host:** `https://pay.nomba.com/sandbox/`

---

## Test Card Numbers

Only the card number determines the checkout outcome. For fields like expiry date and CVV, you can use any future date (e.g., `12/29`) and any 3-digit number (e.g., `123`) unless triggering specific errors.

| Card Number | Network | Expected Outcome |
| :--- | :--- | :--- |
| **`5434 6210 7425 2808`** | MasterCard | OTP Verification Required (OTP Code: `9999` to approve) |
| **`4000 0000 0000 2503`** | Visa | 3DS Authentication Required |
| **`5484 4972 1831 7651`** | MasterCard | Declined (Returns "Do Not Honor") |

---

## PIN and OTP Inputs

When navigating the checkout screens, type the following inputs to verify specific payment state transitions:

*   **Card PIN:** Use **`1234`**
*   **OTP (Successful Charge):** Use **`1234`**
*   **OTP (Timeout):** Use **`1234`**
*   **OTP (Invalid Code):** Use **`5464`**

---

## Simulating Edge-Case Failures

You can trigger specific payment status codes and errors by modifying the request parameters or card values:

*   **Insufficient Funds:** Attempt a charge with an amount greater than **`500,000` NGN**.
*   **Card Expired:** Submit the payment using the card expiry date **`12/20`** (December 2020).
