"""Quick test: verify an API key works against the local server."""
import httpx
import os
import sys
import asyncio

BASE = "http://localhost:8000"

async def main(api_key: str):
    async with httpx.AsyncClient(timeout=10) as client:
        # Test 1: List plans with API key
        print("=" * 50)
        print("TEST 1: GET /api/plans (API key auth)")
        print("=" * 50)
        try:
            r = await client.get(f"{BASE}/api/plans", headers={"Authorization": f"Bearer {api_key}"})
            print(f"  Status: {r.status_code}")
            print(f"  Body:   {r.text[:500]}")
        except Exception as e:
            print(f"  ERROR:  {e}")

        # Test 2: Create a plan with API key
        print("\n" + "=" * 50)
        print("TEST 2: POST /api/plans (create plan with API key)")
        print("=" * 50)
        try:
            payload = {
                "name": "Test Plan via API Key",
                "amount": 2500.00,
                "currency": "NGN",
                "interval_days": 30,
                "trial_days": 7
            }
            r = await client.post(f"{BASE}/api/plans", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload)
            print(f"  Status: {r.status_code}")
            print(f"  Body:   {r.text[:500]}")
        except Exception as e:
            print(f"  ERROR:  {e}")

        # Test 3: Bad API key (should fail)
        print("\n" + "=" * 50)
        print("TEST 3: GET /api/plans (bad API key - should 401)")
        print("=" * 50)
        try:
            r = await client.get(f"{BASE}/api/plans", headers={"Authorization": "Bearer cd_FAKE00_notreal"})
            print(f"  Status: {r.status_code}")
            print(f"  Body:   {r.text[:500]}")
        except Exception as e:
            print(f"  ERROR:  {e}")

        # Test 4: No API key (should fail)
        print("\n" + "=" * 50)
        print("TEST 4: GET /api/plans (no API key - should 401)")
        print("=" * 50)
        try:
            r = await client.get(f"{BASE}/api/plans")
            print(f"  Status: {r.status_code}")
            print(f"  Body:   {r.text[:500]}")
        except Exception as e:
            print(f"  ERROR:  {e}")

if __name__ == "__main__":
    api_key = os.environ.get("CADENCE_API_KEY", "")
    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        print("Error: No CADENCE_API_KEY environment variable set or key passed as an argument.")
        print("Usage: uv run python scripts/test_api_key.py <your_api_key>")
        print("   or: CADENCE_API_KEY=your_key uv run python scripts/test_api_key.py")
        sys.exit(1)

    asyncio.run(main(api_key))
