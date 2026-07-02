import asyncio
import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.event import Event
from app.core.nomba_client import nomba_client
from app.services.billing_service import BillingService

class DunningService:
    @staticmethod
    async def process_renewal(db: Session, subscription: Subscription) -> bool:
        """Attempt to charge the tokenized card for renewal."""
        import json
        
        if subscription.cancel_at_period_end:
            print(f"[DUNNING] Subscription {subscription.id} is scheduled for cancellation at period end. Cancelling now.")
            BillingService.cancel_subscription(db, subscription)
            return False

        if not subscription.token_key:
            print(f"[DUNNING] No card token available for subscription: {subscription.id}")
            if subscription.status == "trialing":
                BillingService.transition_state(db, subscription, "cancelled")
                subscription.cancelled_at = datetime.utcnow()
                event_type = "subscription.cancelled"
            elif subscription.status in ("active", "past_due"):
                BillingService.transition_state(db, subscription, "suspended")
                event_type = "subscription.suspended"
            else:
                event_type = None

            if event_type:
                event = Event(
                    project_id=subscription.project_id,
                    subscription_id=subscription.id,
                    event_type=event_type,
                    data_json=json.dumps({
                        "subscription_id": subscription.id,
                        "reason": "token_key_missing",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                )
                db.add(event)
                db.add(subscription)
                db.commit()
            return False

        # --- PRE-FLIGHT VERIFICATION RECOVERY ---
        # Find any pending payment attempts from the current cycle
        existing_pending = db.query(Payment).filter(
            Payment.subscription_id == subscription.id,
            Payment.status == "pending",
            Payment.created_at >= subscription.current_period_start
        ).first()

        if existing_pending:
            try:
                print(f"[DUNNING] Pre-flight: Checking if pending payment {existing_pending.nomba_order_ref} succeeded downstream...")
                verification = await nomba_client.verify_transaction(
                    db,
                    subscription.project,
                    existing_pending.nomba_order_ref
                )
                code = verification.get("code")
                data = verification.get("data", {}) or {}
                status = data.get("status")
                txn_id = data.get("transactionId")

                if code == "00" or status == "SUCCESS":
                    BillingService.process_payment_success(
                        db,
                        existing_pending.nomba_order_ref,
                        txn_id
                    )
                    print(f"[DUNNING] Recovered successfully from prior uncommitted state. Subscription {subscription.id} advanced.")
                    return True
            except Exception as e:
                print(f"[DUNNING] Pre-flight check failed: {e}. Continuing with renewal process...")
        # --- END PRE-FLIGHT VERIFICATION ---

        plan = subscription.plan
        project = subscription.project
        order_ref = f"cadence_renew_{subscription.id[:8]}_{int(datetime.utcnow().timestamp())}"
        idempotency_key = f"idemp_{subscription.id}_{subscription.retry_count}_{subscription.current_period_end.strftime('%Y%m%d')}"

        # Create pending Payment record
        payment = Payment(
            subscription_id=subscription.id,
            project_id=subscription.project_id,
            amount=plan.amount,
            currency=plan.currency,
            nomba_order_ref=order_ref,
            status="pending",
            idempotency_key=idempotency_key
        )
        db.add(payment)
        db.commit()

        try:
            print(f"[DUNNING] Charging card token for subscription: {subscription.id} (amount: {plan.amount})")
            sub_acc_id = plan.api_key.nomba_sub_account_id if plan.api_key else None
            resp = await nomba_client.charge_tokenized_card(
                db=db,
                project=project,
                token_key=subscription.token_key,
                order_ref=order_ref,
                amount=float(plan.amount),
                idempotency_key=idempotency_key,
                currency=str(plan.currency),
                sub_account_id=sub_acc_id
            )
            
            # Check response code
            code = resp.get("code")
            data = resp.get("data", {})
            status = data.get("status") or resp.get("status")
            transaction_id = data.get("transactionId")
            
            if code == "00" or status == "SUCCESS":
                BillingService.process_payment_success(db, order_ref, transaction_id)
                print(f"[DUNNING] Renewal payment succeeded for subscription: {subscription.id}")
                return True
            else:
                print(f"[DUNNING] Renewal payment declined/failed for subscription: {subscription.id} response: {resp}")
                BillingService.process_payment_failure(db, order_ref)
                DunningService.handle_failure(db, subscription)
                return False
                
        except (httpx.TimeoutException, httpx.NetworkError, asyncio.TimeoutError) as e:
            print(f"[DUNNING] Network timeout during card charge for sub {subscription.id}, order {order_ref}: {type(e).__name__} - {str(e)}")
            # Do not change payment status; allow pre-flight verification to check it later
            return False
        except Exception as e:
            print(f"[DUNNING] Error occurred during card charge for sub {subscription.id}, order {order_ref}: {type(e).__name__} - {str(e)}")
            payment.status = "failed"
            db.add(payment)
            DunningService.handle_failure(db, subscription)
            db.commit()
            return False

    @staticmethod
    def handle_failure(db: Session, subscription: Subscription) -> None:
        """Handle retry scheduling escalations on payment failure."""
        now = datetime.utcnow()
        if subscription.status == "active":
            BillingService.transition_state(db, subscription, "past_due")
            subscription.retry_count = 0
            
        subscription.retry_count += 1
        
        # Schedule next attempt
        if subscription.retry_count == 1:
            subscription.next_retry_at = now + timedelta(days=1)
        elif subscription.retry_count == 2:
            subscription.next_retry_at = now + timedelta(days=3)
        elif subscription.retry_count == 3:
            subscription.next_retry_at = now + timedelta(days=7)
        else:
            # All retries exhausted, suspend subscription
            subscription.next_retry_at = None
            BillingService.transition_state(db, subscription, "suspended")
            
        db.add(subscription)
        db.commit()

    @staticmethod
    async def run_dunning_cycle(db: Session) -> None:
        """Run a single pass of the dunning & automatic renewal scheduler."""
        now = datetime.utcnow()

        # 1. Select active subscriptions that have reached period end and need renewal
        due_renewals = db.query(Subscription).filter(
            Subscription.status == "active",
            Subscription.current_period_end <= now
        ).with_for_update(skip_locked=True).all()

        for sub in due_renewals:
            await DunningService.process_renewal(db, sub)

        # 2. Select past_due subscriptions that are scheduled for retry
        due_retries = db.query(Subscription).filter(
            Subscription.status == "past_due",
            Subscription.next_retry_at <= now
        ).with_for_update(skip_locked=True).all()

        for sub in due_retries:
            await DunningService.process_renewal(db, sub)
