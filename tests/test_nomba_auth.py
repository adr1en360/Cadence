import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

# Load env variables from .env
load_dotenv()

SANDBOX_BASE = "https://sandbox.nomba.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

def run_auth_test():
    print("[*] Loading Nomba credentials from .env...")
    client_id = os.getenv("NOMBA_CLIENT_ID")
    client_secret = os.getenv("NOMBA_CLIENT_SECRET")
    account_id = os.getenv("NOMBA_ACCOUNT_ID")

    if not all([client_id, client_secret, account_id]):
        print("[ERROR] Missing required Nomba credentials in .env file.")
        print(f"  NOMBA_CLIENT_ID: {'Loaded' if client_id else 'MISSING'}")
        print(f"  NOMBA_CLIENT_SECRET: {'Loaded' if client_secret else 'MISSING'}")
        print(f"  NOMBA_ACCOUNT_ID: {'Loaded' if account_id else 'MISSING'}")
        return False

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

    print(f"[*] Dispatching token request to {url}...")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            print("[OK] Authenticated successfully!")
            token = result.get("data", {}).get("access_token")
            if token:
                print(f"  Access Token: {token[:20]}... [length: {len(token)}]")
                return True
            else:
                print("[ERROR] Token not found in response data structure.")
                print(json.dumps(result, indent=2))
                return False
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP Authentication Error {e.code}")
        try:
            print(f"  Response: {e.read().decode('utf-8')}")
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def test_auth():
    assert run_auth_test() is True

if __name__ == "__main__":
    success = run_auth_test()
    import sys
    sys.exit(0 if success else 1)
