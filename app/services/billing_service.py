from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.event import Event
from app.models.plan import Plan
from app.models.merchant import Merchant
from app.core.nomba_client import nomba_client

VALID_TRANSITIONS = {
    "trialing":  ["active", "cancelled"],
    "active":    ["past_due", "cancelled", "expired"],
    "past_due":  ["active", "suspended"],
    "suspended": ["active", "cancelled"],
    "cancelled": [],   # terminal
    "expired":   [],   # terminal
}

class BillingService:
    @staticmethod
    def transition_state(db: Session, subscription: Subscription, new_state: str) -> None:
        """Enforce strict state machine transitions and log the event."""
        old_state = subscription.status
        if old_state == new_state:
            return
            
        allowed = VALID_TRANSITIONS.get(old_state, [])
        if new_state not in allowed:
            raise ValueError(f"Invalid subscription state transition from '{old_state}' to '{new_state}'")
            
        subscription.status = new_state
        subscription.updated_at = datetime.utcnow()
        db.add(subscription)
        
        # Log to Event audit log
        event = Event(
            merchant_id=subscription.merchant_id,
            subscription_id=subscription.id,
            event_type=f"subscription.status_updated",
            data_json=json.dumps({
                "subscription_id": subscription.id,
                "old_state": old_state,
                "new_state": new_state,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        db.add(event)

    @staticmethod
    async def create_subscription(
        db: Session,
        merchant: Merchant,
        plan: Plan,
        customer_email: str,
        customer_name: str,
        callback_url: str
    ) -> tuple[Subscription, str]:
        """Initialize subscription and create a tokenized checkout order with Nomba."""
        # Check if plan has trial
        now = datetime.utcnow()
        has_trial = plan.trial_days and plan.trial_days > 0
        
        trial_end = now + timedelta(days=float(plan.trial_days)) if has_trial else None
        current_period_start = now
        current_period_end = trial_end if has_trial else now + timedelta(days=float(plan.interval_days))
        
        # Create Subscription record (starts as pending/trialing or active pending checkout)
        subscription = Subscription(
            merchant_id=merchant.id,
            plan_id=plan.id,
            customer_email=customer_email,
            customer_name=customer_name,
            status="trialing" if has_trial else "active",
            trial_end=trial_end,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Generate unique order reference
        order_ref = f"cadence_sub_{subscription.id[:8]}_{int(now.timestamp())}"
        
        # Determine charge amount: if trialing, checkouts are usually a token auth charge (like ₦50 or ₦100) or free order
        # For simplicity, we create a checkout order for the plan amount (or first payment)
        charge_amount = float(plan.amount)
        
        # Create checkout order via Nomba client
        sub_acc_id = plan.api_key.nomba_sub_account_id if plan.api_key else None
        checkout_resp = await nomba_client.create_checkout_order(
            order_ref=order_ref,
            amount=charge_amount,
            customer_email=customer_email,
            callback_url=callback_url,
            currency=str(plan.currency),
            sub_account_id=sub_acc_id
        )
        
        checkout_link = checkout_resp.get("data", {}).get("checkoutLink") or checkout_resp.get("checkoutLink")
        if not checkout_link:
            raise RuntimeError(f"Nomba failed to return a checkoutLink: {checkout_resp}")
            
        # Create pending Payment record
        payment = Payment(
            subscription_id=subscription.id,
            merchant_id=merchant.id,
            amount=plan.amount,
            currency=plan.currency,
            nomba_order_ref=order_ref,
            status="pending"
        )
        db.add(payment)
        db.commit()
        
        return subscription, checkout_link

    @staticmethod
    def process_payment_success(db: Session, nomba_order_ref: str, transaction_id: str, token_key: str = None) -> Subscription:
        """Handle successful checkout or tokenized card payment outcome."""
        payment = db.query(Payment).filter(Payment.nomba_order_ref == nomba_order_ref).first()
        if not payment:
            raise ValueError(f"No payment record found for order reference: {nomba_order_ref}")
            
        if payment.status == "succeeded":
            return payment.subscription
            
        payment.status = "succeeded"
        payment.nomba_transaction_id = transaction_id
        db.add(payment)
        
        subscription = payment.subscription
        
        # Update token key if provided
        if token_key:
            subscription.token_key = token_key
            
        # Update period window
        now = datetime.utcnow()
        plan = subscription.plan
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=float(plan.interval_days))
        
        # Reset dunning retries
        subscription.retry_count = 0
        subscription.next_retry_at = None
        
        # Transition subscription back/to active status
        if subscription.status in ["trialing", "past_due", "suspended"]:
            BillingService.transition_state(db, subscription, "active")
        else:
            db.add(subscription)
            
        db.commit()
        return subscription

    @staticmethod
    def process_payment_failure(db: Session, nomba_order_ref: str) -> Subscription:
        """Handle failed payment attempts (triggers dunning state if active)."""
        payment = db.query(Payment).filter(Payment.nomba_order_ref == nomba_order_ref).first()
        if not payment:
            raise ValueError(f"No payment record found for order reference: {nomba_order_ref}")
            
        if payment.status == "failed":
            return payment.subscription
            
        payment.status = "failed"
        db.add(payment)
        
        subscription = payment.subscription
        
        # Active subscriptions transition to past_due
        if subscription.status == "active":
            BillingService.transition_state(db, subscription, "past_due")
            
        db.commit()
        return subscription

    @staticmethod
    def cancel_subscription(db: Session, subscription: Subscription) -> None:
        """Cancel a subscription immediately."""
        BillingService.transition_state(db, subscription, "cancelled")
        subscription.cancelled_at = datetime.utcnow()
        db.add(subscription)
        db.commit()
