"""
Nomba Sandbox Checkout Creator -- tokenKey Discovery Test
Creates a checkout order with tokenizeCard=true on the Nomba sandbox.

TWO MODES:
  1. No-auth mode: POST /v1/checkout/order (no credentials needed, limited features)
  2. Auth mode:    POST /sandbox/checkout/order (requires Bearer token + accountId)

The no-auth mode (POST /v1/checkout/order) works without credentials.
The auth mode (POST /sandbox/checkout/order) requires sandbox credentials.
We try no-auth first. Pass --auth to use authenticated mode.
"""
import json
import sys
import urllib.request
import urllib.error

SANDBOX_BASE = "https://sandbox.nomba.com"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def get_sandbox_token(client_id: str, client_secret: str, account_id: str) -> str:
    """Exchange credentials for a sandbox access token."""
    url = f"{SANDBOX_BASE}/v1/auth/token/issue"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "accountId": account_id,
            "User-Agent": UA,
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["data"]["access_token"]


def create_tokenized_checkout(callback_url: str, token: str = None, account_id: str = None):
    """Create a checkout order with card tokenization enabled."""

    # Choose endpoint based on auth mode
    if token and account_id:
        endpoint = f"{SANDBOX_BASE}/sandbox/checkout/order"
        mode = "AUTHENTICATED (sandbox/checkout/order)"
    else:
        endpoint = f"{SANDBOX_BASE}/v1/checkout/order"
        mode = "NO-AUTH (v1/checkout/order)"

    payload = {
        "order": {
            "orderReference": "cadence_token_test_002",
            "amount": "100.00",
            "currency": "NGN",
            "customerEmail": "test@cadence.dev",
            "callbackUrl": callback_url,
        },
        "tokenizeCard": True,
        "allowedPaymentMethods": ["Card"],
    }

    print(f"\n[*] Creating tokenized checkout order...")
    print(f"    Mode: {mode}")
    print(f"    Endpoint: {endpoint}")
    print(f"    Callback URL: {callback_url}")
    print(f"    Payload:")
    print(json.dumps(payload, indent=2))

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": UA,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if account_id:
        headers["accountId"] = account_id

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            response_body = resp.read().decode("utf-8")
            response_json = json.loads(response_body)

            print(f"\n[OK] Checkout order created!")
            print(f"     Full response:")
            print(json.dumps(response_json, indent=2))

            # Try to find the checkout link
            checkout_link = None
            if isinstance(response_json, dict):
                checkout_link = (
                    response_json.get("checkoutLink")
                    or response_json.get("data", {}).get("checkoutLink")
                    or response_json.get("result", {}).get("checkoutLink")
                )

            if checkout_link:
                print(f"\n[LINK] CHECKOUT LINK: {checkout_link}")
                print(f"\n   Next steps:")
                print(f"   1. Open this link in your browser")
                print(f"   2. Enter card: 5434621074252808")
                print(f"   3. Expiry: any future date (e.g., 12/30)")
                print(f"   4. CVV: any 3 digits (e.g., 123)")
                print(f"   5. PIN: 1234")
                print(f"   6. OTP: 1234")
                print(f"   7. Watch webhook_receiver.py terminal for the payload")
            else:
                print(f"\n[!] Could not find checkoutLink in response. Check the full response above.")

            return response_json

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"\n[ERROR] HTTP Error {e.code}")
        print(f"   Response: {error_body}")
        return None
    except urllib.error.URLError as e:
        print(f"\n[ERROR] Connection Error: {e.reason}")
        return None


def print_usage():
    print("Usage:")
    print("  No-auth mode (try first):")
    print("    uv run scripts/create_checkout.py <ngrok_https_url>")
    print("")
    print("  Auth mode (if no-auth doesn't support tokenizeCard):")
    print("    uv run scripts/create_checkout.py --auth <ngrok_https_url> <client_id> <client_secret> <account_id>")
    print("")
    print("Example:")
    print("  uv run scripts/create_checkout.py https://abc123.ngrok-free.app")
    print("  uv run scripts/create_checkout.py --auth https://abc123.ngrok-free.app my_client_id my_client_secret my_account_id")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    if sys.argv[1] == "--auth":
        if len(sys.argv) < 6:
            print("[ERROR] Auth mode requires: <ngrok_url> <client_id> <client_secret> <account_id>")
            print_usage()
            sys.exit(1)
        ngrok_url = sys.argv[2].rstrip("/")
        client_id = sys.argv[3]
        client_secret = sys.argv[4]
        account_id = sys.argv[5]

        print(f"[*] Getting sandbox access token...")
        try:
            token = get_sandbox_token(client_id, client_secret, account_id)
            print(f"[OK] Got access token: {token[:20]}...")
        except Exception as e:
            print(f"[ERROR] Failed to get token: {e}")
            sys.exit(1)

        callback_url = f"{ngrok_url}/webhooks/nomba"
        create_tokenized_checkout(callback_url, token=token, account_id=account_id)
    else:
        ngrok_url = sys.argv[1].rstrip("/")
        callback_url = f"{ngrok_url}/webhooks/nomba"
        create_tokenized_checkout(callback_url)
