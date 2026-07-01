import asyncio
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
        if not subscription.token_key:
            # No tokenized card key present, transition straight to past_due or suspended
            print(f"[DUNNING] No card token available for subscription: {subscription.id}")
            if subscription.status == "active":
                BillingService.transition_state(db, subscription, "past_due")
                subscription.retry_count = 0
                subscription.next_retry_at = datetime.utcnow() + timedelta(days=1)
                db.add(subscription)
                db.commit()
            return False

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
                
        except Exception as e:
            print(f"[DUNNING] Error occurred during card charge: {e}")
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
