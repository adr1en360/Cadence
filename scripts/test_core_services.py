import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.nomba_client import nomba_client
from app.core.security import hash_password, generate_api_key_prefix_and_secret
from app.models.project import Project
from app.models.merchant import Merchant, APIKey
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.services.billing_service import BillingService
from app.services.dunning_service import DunningService

load_dotenv()

async def test_integration():
    print("[*] Starting Core Services Verification Script...")
    
    # 1. DB Session Check
    print("[*] Creating database session...")
    db = SessionLocal()
    try:
        merchants_count = db.query(Merchant).count()
        print(f"[OK] Database connection verified. Existing merchants in DB: {merchants_count}")
    except Exception as e:
        print(f"[ERROR] Database verification failed: {e}")
        db.close()
        return False

    # 2. Test Merchant, Project & Plan Setup
    print("[*] Creating test merchant, project, and plan records in local database...")
    try:
        # Create a mock merchant
        test_email = f"merchant_{int(asyncio.get_event_loop().time())}@test.com"
        prefix, plain_key, hashed_key = generate_api_key_prefix_and_secret()
        
        merchant = Merchant(
            name="Test Cadence Merchant",
            email=test_email,
            password_hash=hash_password("securepassword123")
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)
        print(f"[OK] Created test merchant: {merchant.name} (ID: {merchant.id})")

        # Create project
        project = Project(
            merchant_id=merchant.id,
            name="SchoolPadi Test Project",
            nomba_client_id=os.getenv("NOMBA_CLIENT_ID"),
            nomba_client_secret_encrypted=os.getenv("NOMBA_CLIENT_SECRET"),
            nomba_account_id=os.getenv("NOMBA_ACCOUNT_ID")
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"[OK] Created test project: {project.name} (ID: {project.id})")

        # Create api key record
        api_key = APIKey(
            project_id=project.id,
            key_hash=hashed_key,
            key_prefix=prefix,
            label="Default Test Key"
        )
        db.add(api_key)
        
        # Create a test plan (e.g., Monthly Plan at ₦2,000)
        plan = Plan(
            project_id=project.id,
            name="Pro Monthly Subscription",
            amount=2000.00,
            currency="NGN",
            interval_days=30,
            trial_days=0
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        print(f"[OK] Created test plan: {plan.name} (Amount: {plan.amount} NGN)")

    except Exception as e:
        print(f"[ERROR] DB Record seeding failed: {e}")
        db.rollback()
        db.close()
        return False

    # 3. Test Billing Service Subscription Flow
    print("[*] Simulating checkout creation via billing_service...")
    try:
        # Create subscription with checkout url mapping
        callback_url = "https://localhost:8000/webhooks/nomba"
        subscription, checkout_link, _ = await BillingService.create_subscription(
            db=db,
            project=project,
            plan=plan,
            customer_email="customer@schoolpadi.ng",
            customer_name="Emeka Eze",
            callback_url=callback_url
        )
        
        print("[OK] Subscription initialized and checkout link generated successfully!")
        print(f"  Subscription ID: {subscription.id}")
        print(f"  Initial Status: {subscription.status}")
        print(f"  Checkout Link: {checkout_link[:60]}...")
        
        # Validate state machine transition logic
        print("[*] Transitioning pending_payment -> active...")
        BillingService.transition_state(db, subscription, "active")
        print("[*] Testing state transition validations (active -> past_due)...")
        BillingService.transition_state(db, subscription, "past_due")
        db.commit()
        print(f"[OK] Successfully transitioned subscription status to: {subscription.status}")
        
        try:
            # Enforce invalid transition (past_due -> trialing should fail)
            print("[*] Attempting invalid state transition (past_due -> trialing)...")
            BillingService.transition_state(db, subscription, "trialing")
        except ValueError as e:
            print(f"[OK] Invalid transition correctly blocked by validator: {e}")
            
    except Exception as e:
        print(f"[ERROR] Billing service execution failed: {e}")
        db.rollback()
        db.close()
        return False

    # Clean up test records
    print("[*] Cleaning up test records from local DB...")
    try:
        # Cascade will delete projects, keys, subscriptions, payments, and events
        db.delete(merchant)
        db.commit()
        print("[OK] Test database records cleaned up successfully.")
    except Exception as e:
        print(f"[WARNING] Database cleanup failed: {e}")

    db.close()
    print("[SUCCESS] Core services integration verification complete!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    import sys
    sys.exit(0 if success else 1)
