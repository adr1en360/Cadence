# Nomba API AI/LLM Context Index

> [!NOTE]
> This index is fetched directly from Nomba's official developer documentation `llms.txt` at `https://developer.nomba.com/llms.txt`.
> Whenever you need up-to-date, detailed schemas, header specifications, or payload details for any Nomba API endpoint, you should refer to this index and use the `read_url_content` tool to fetch the relevant URL directly.

## How to Get Detailed Nomba API Info
1. Locate the endpoint or product feature you need in the list below.
2. Call the `read_url_content` tool with the corresponding URL (e.g., `https://developer.nomba.com/docs/products/accept-payment/recurring-payments.md`).
3. Parse the returned markdown for exact fields, parameters, and headers.

---

## Nomba Developer Documentation Index

### Core & Basics
*   [AI Tools Overview](https://developer.nomba.com/developer-resources/ai-tools/overview.md)
*   [Environment Setup (Sandbox/Prod)](https://developer.nomba.com/docs/api-basics/environment.md)
*   [API Key Setup](https://developer.nomba.com/docs/getting-started/get-api-keys.md)
*   [Authentication Guide](https://developer.nomba.com/docs/getting-started/authentication.md)
*   [Authentication Best Practices](https://developer.nomba.com/docs/guides/authentication-best-practises.md)
*   [Error Codes Reference](https://developer.nomba.com/docs/api-basics/error-codes.md)
*   [Rate Limits](https://developer.nomba.com/docs/api-basics/rate_limit.md)
*   [Sandbox Testing Details](https://developer.nomba.com/docs/api-basics/testing.md)
*   [Pagination Guide](https://developer.nomba.com/docs/api-basics/pagination.md)

### Webhooks
*   [Webhooks Overview](https://developer.nomba.com/docs/api-basics/webhook.md)
*   [Setting Up Webhooks](https://developer.nomba.com/docs/guides/setting-up-webhooks.md)
*   [Debugging and Troubleshooting Webhooks](https://developer.nomba.com/docs/api-basics/troubleshoot-webhooks.md)

### Accept Online Payments (Checkout)
*   [Accept Online Payments Guide](https://developer.nomba.com/docs/guides/accept-online-payments.md)
*   [Checkout Overview](https://developer.nomba.com/docs/products/accept-payment/checkout-overview.md)
*   [Create a Checkout Order](https://developer.nomba.com/docs/products/accept-payment/create-checkout-order.md)
*   [Cancel a Checkout Order](https://developer.nomba.com/docs/products/accept-payment/cancel-checkout-order.md)
*   [Refund a Checkout Order](https://developer.nomba.com/docs/products/accept-payment/refund-checkout-order.md)
*   [Verify Transactions](https://developer.nomba.com/docs/products/accept-payment/verify-transactions.md)
*   [Payment Methods Supported](https://developer.nomba.com/docs/products/accept-payment/payment-methods.md)
*   [Direct Debit Guide](https://developer.nomba.com/docs/products/accept-payment/direct-debit.md)
*   [Server-to-Server Charge API](https://developer.nomba.com/docs/products/accept-payment/server-to-server.md)
*   [Sandbox Testing Checklist](https://developer.nomba.com/docs/products/accept-payment/sandbox-testing.md)

### Recurring & Tokenization
*   [Recurring Payments (Tokenized Card Payment)](https://developer.nomba.com/docs/products/accept-payment/recurring-payments.md)

### Nomba API Reference Endpoints
*   [Obtain Access Token API](https://developer.nomba.com/nomba-api-reference/authenticate/obtain-access-token.md)
*   [Refresh Token API](https://developer.nomba.com/nomba-api-reference/authenticate/refresh-an-expired-token.md)
*   [Revoke Token API](https://developer.nomba.com/nomba-api-reference/authenticate/revoke-an-access_token.md)
*   [Create Online Checkout Order API](https://developer.nomba.com/nomba-api-reference/online-checkout/create-an-online-checkout-order.md)
*   [Charge Customer with Tokenized Card API](https://developer.nomba.com/nomba-api-reference/online-checkout/charge-a-customer-using-tokenized-card-data.md)
*   [List Tokenized Cards API](https://developer.nomba.com/nomba-api-reference/online-checkout/list-tokenized-cards.md)
*   [Delete Tokenized Card API](https://developer.nomba.com/nomba-api-reference/online-checkout/delete-tokenized-card-data.md)
*   [Update Tokenized Card API](https://developer.nomba.com/nomba-api-reference/online-checkout/update-tokenized-card-data.md)
*   [Refund Checkout Transaction API](https://developer.nomba.com/nomba-api-reference/online-checkout/refund-checkout-transaction.md)
*   [Cancel Checkout Order API](https://developer.nomba.com/nomba-api-reference/online-checkout/cancel-checkout-order.md)
*   [Fetch Checkout Transaction API](https://developer.nomba.com/nomba-api-reference/online-checkout/fetch-checkout-transaction.md)

### Direct Debits & Mandates
*   [Create Direct Debit Mandate API](https://developer.nomba.com/nomba-api-reference/direct-debits/create-direct-debit.md)
*   [Debit a Mandate API](https://developer.nomba.com/nomba-api-reference/direct-debits/debit-mandate.md)
*   [Get Mandate Status API](https://developer.nomba.com/nomba-api-reference/direct-debits/check-direct-debit-status.md)
*   [List Direct Debit Mandates API](https://developer.nomba.com/nomba-api-reference/direct-debits/list-direct-debit-mandates.md)
*   [Update Mandate Status API](https://developer.nomba.com/nomba-api-reference/direct-debits/update-direct-debit-status.md)

### Transfers & Payouts (Nigerian Banks)
*   [Overview of Transfers](https://developer.nomba.com/docs/products/transfers/introduction.md)
*   [Fetch Bank Codes and Names](https://developer.nomba.com/nomba-api-reference/transfers/fetch-bank-codes-and-names.md)
*   [Bank Account Lookup API](https://developer.nomba.com/nomba-api-reference/transfers/perform-bank-account-lookup.md)
*   [Perform Bank Transfer (Parent Account)](https://developer.nomba.com/nomba-api-reference/transfers/perform-bank-account-transfer-from-the-parent-account.md)
*   [Perform Bank Transfer (Sub-account)](https://developer.nomba.com/nomba-api-reference/transfers/perform-bank-account-transfer-from-the-sub-account.md)
*   [Wallet Transfer (Parent Account)](https://developer.nomba.com/nomba-api-reference/transfers/perform-wallet-transfer-from-the-parent-account.md)
*   [Wallet Transfer (Sub-account)](https://developer.nomba.com/nomba-api-reference/transfers/perform-wallet-transfer-from-a-sub-account.md)

### Sub-accounts & Terminals
*   [Fetch Parent Account Details](https://developer.nomba.com/nomba-api-reference/accounts/fetch-parent-account-details.md)
*   [Fetch Parent Account Balance](https://developer.nomba.com/nomba-api-reference/accounts/fetch-parent-account-balance.md)
*   [Fetch Sub-account Details](https://developer.nomba.com/nomba-api-reference/accounts/fetch-sub-account-details.md)
*   [Fetch Sub-account Balance](https://developer.nomba.com/nomba-api-reference/accounts/fetch-sub-account-balance.md)
*   [Assign Terminal to Parent](https://developer.nomba.com/nomba-api-reference/terminals/assign-a-terminal-to-the-parent-account.md)
*   [Assign Terminal to Sub-account](https://developer.nomba.com/nomba-api-reference/terminals/assign-a-terminal-to-a-sub-account.md)

### Virtual Accounts
*   [Create Virtual Account API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/create-virtual-account.md)
*   [Create Virtual Account for Sub-account API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/create-virtual-account-for-sub-account.md)
*   [Fetch Virtual Account API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/fetch-a-virtual-account.md)
*   [Update Virtual Account API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/update-a-virtual-account.md)
*   [Expire Virtual Account API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/expire-a-virtual-account.md)
*   [Filter Virtual Accounts API](https://developer.nomba.com/nomba-api-reference/virtual-accounts/filter-virtual-accounts.md)

### OpenAPI Definition
*   [openapi.json](https://developer.nomba.com/nomba-api-reference/openapi.json)
