import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from app.core.database import SessionLocal
from app.services.dunning_service import DunningService

async def main():
    print("[*] Running Cadence Dunning & Renewal Cycle...")
    db = SessionLocal()
    try:
        await DunningService.run_dunning_cycle(db)
        print("[SUCCESS] Dunning cycle completed.")
    except Exception as e:
        print(f"[ERROR] Dunning cycle failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
