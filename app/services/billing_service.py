from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import json
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.models.event import Event
from app.models.plan import Plan
from app.models.project import Project
from app.core.nomba_client import nomba_client

VALID_TRANSITIONS = {
    "pending_payment": ["active", "cancelled"],
    "trialing":  ["active", "cancelled"],
    "active":    ["past_due", "cancelled", "expired", "suspended"],
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
            project_id=subscription.project_id,
            subscription_id=subscription.id,
            event_type="subscription.status_updated",
            data_json=json.dumps({
                "subscription_id": subscription.id,
                "old_state": old_state,
                "new_state": new_state,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        db.add(event)

        # Dispatch webhook to merchant
        from app.services.webhook_dispatcher import dispatch_webhook
        dispatch_webhook(
            project=subscription.project,
            event_type="subscription.status_updated",
            data={
                "subscription_id": subscription.id,
                "old_state": old_state,
                "new_state": new_state,
                "customer_email": subscription.customer_email
            }
        )

    @staticmethod
    async def create_subscription(
        db: Session,
        project: Project,
        plan: Plan,
        customer_email: str,
        customer_name: str,
        callback_url: str
    ) -> tuple[Subscription, str, str]:
        """Initialize subscription and create a tokenized checkout order with Nomba."""
        now = datetime.utcnow()
        has_trial = plan.trial_days and plan.trial_days > 0
        
        trial_end = now + timedelta(days=float(plan.trial_days)) if has_trial else None
        current_period_start = now
        current_period_end = trial_end if has_trial else now + timedelta(days=float(plan.interval_days))
        
        # Create Subscription record (starts as pending/trialing or active pending checkout)
        subscription = Subscription(
            project_id=project.id,
            plan_id=plan.id,
            customer_email=customer_email,
            customer_name=customer_name,
            status="trialing" if has_trial else "pending_payment",
            trial_end=trial_end,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        # Generate unique order reference
        order_ref = f"cadence_sub_{subscription.id[:8]}_{int(now.timestamp())}"
        charge_amount = float(plan.amount)
        
        # Create checkout order via Nomba client
        sub_acc_id = plan.api_key.nomba_sub_account_id if plan.api_key else None
        checkout_resp = await nomba_client.create_checkout_order(
            db=db,
            project=project,
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
            project_id=project.id,
            amount=plan.amount,
            currency=plan.currency,
            nomba_order_ref=order_ref,
            status="pending",
            idempotency_key=f"idemp_{subscription.id}_{order_ref}"
        )
        db.add(payment)
        db.commit()
        
        return subscription, checkout_link, order_ref

    @staticmethod
    def process_payment_success(
        db: Session,
        nomba_order_ref: str,
        transaction_id: str,
        token_key: str = None,
        card_brand: str = None,
        card_last4: str = None
    ) -> Subscription:
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
        
        # Update token key and card details if provided
        if token_key:
            subscription.token_key = token_key
        if card_brand:
            subscription.card_brand = card_brand
        if card_last4:
            subscription.card_last4 = card_last4
            
        # Update period window
        now = datetime.utcnow()
        plan = subscription.plan
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=float(plan.interval_days))
        
        # Reset dunning retries
        subscription.retry_count = 0
        subscription.next_retry_at = None
        
        # Transition subscription back/to active status
        if subscription.status in ["pending_payment", "trialing", "past_due", "suspended"]:
            BillingService.transition_state(db, subscription, "active")
        else:
            db.add(subscription)
            
        # Create Event for successful payment
        event = Event(
            project_id=subscription.project_id,
            subscription_id=subscription.id,
            event_type="payment.succeeded",
            data_json=json.dumps({
                "subscription_id": subscription.id,
                "nomba_order_ref": nomba_order_ref,
                "nomba_transaction_id": transaction_id,
                "amount": float(payment.amount),
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        db.add(event)
        
        # Dispatch webhook to merchant
        from app.services.webhook_dispatcher import dispatch_webhook
        dispatch_webhook(
            project=subscription.project,
            event_type="payment.succeeded",
            data={
                "subscription_id": subscription.id,
                "nomba_order_ref": nomba_order_ref,
                "nomba_transaction_id": transaction_id,
                "amount": float(payment.amount),
                "customer_email": subscription.customer_email
            }
        )
        
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
            
        # Create Event for failed payment
        event = Event(
            project_id=subscription.project_id,
            subscription_id=subscription.id,
            event_type="payment.failed",
            data_json=json.dumps({
                "subscription_id": subscription.id,
                "nomba_order_ref": nomba_order_ref,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        db.add(event)

        # Dispatch webhook to merchant
        from app.services.webhook_dispatcher import dispatch_webhook
        dispatch_webhook(
            project=subscription.project,
            event_type="payment.failed",
            data={
                "subscription_id": subscription.id,
                "nomba_order_ref": nomba_order_ref,
                "customer_email": subscription.customer_email
            }
        )
        
        db.commit()
        return subscription

    @staticmethod
    def cancel_subscription(db: Session, subscription: Subscription) -> None:
        """Cancel a subscription immediately."""
        BillingService.transition_state(db, subscription, "cancelled")
        subscription.cancelled_at = datetime.utcnow()
        db.add(subscription)
        
        # Create Event for cancellation
        event = Event(
            project_id=subscription.project_id,
            subscription_id=subscription.id,
            event_type="subscription.cancelled",
            data_json=json.dumps({
                "subscription_id": subscription.id,
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        db.add(event)

        # Dispatch webhook to merchant
        from app.services.webhook_dispatcher import dispatch_webhook
        dispatch_webhook(
            project=subscription.project,
            event_type="subscription.cancelled",
            data={
                "subscription_id": subscription.id,
                "customer_email": subscription.customer_email
            }
        )

        db.commit()

    @staticmethod
    async def refund_payment(db: Session, payment: Payment, project: Project) -> dict:
        """Refund a payment transaction via Nomba client."""
        import json
        from datetime import datetime
        from app.services.webhook_dispatcher import dispatch_webhook
        
        resp = await nomba_client.refund_transaction(
            db=db,
            project=project,
            transaction_id=payment.nomba_transaction_id,
            amount=float(payment.amount)
        )
        
        code = resp.get("code")
        status_val = resp.get("status")
        
        # Depending on sandbox/production structure, success is code "00" or status SUCCESS
        if code == "00" or status_val == "SUCCESS" or resp.get("data", {}).get("status") == "SUCCESS":
            payment.status = "refunded"
            db.add(payment)
            
            # Log refund event
            event = Event(
                project_id=project.id,
                subscription_id=payment.subscription_id,
                event_type="payment.refunded",
                data_json=json.dumps({
                    "payment_id": payment.id,
                    "nomba_transaction_id": payment.nomba_transaction_id,
                    "amount": float(payment.amount),
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            db.add(event)
            
            # Dispatch webhook to merchant
            dispatch_webhook(
                project=project,
                event_type="payment.refunded",
                data={
                    "payment_id": payment.id,
                    "nomba_transaction_id": payment.nomba_transaction_id,
                    "amount": float(payment.amount),
                    "customer_email": payment.subscription.customer_email if payment.subscription else None
                }
            )
            
            db.commit()
            return {"status": "refunded"}
        else:
            raise RuntimeError(f"Nomba refund rejected: {resp}")

    @staticmethod
    def generate_portal_link(db: Session, subscription: Subscription, base_url: str) -> dict:
        """Generate tokenized magic URL for self-service customer portal."""
        import secrets
        from datetime import datetime, timedelta
        
        token = secrets.token_urlsafe(32)
        subscription.portal_token = token
        subscription.portal_token_expires_at = datetime.utcnow() + timedelta(hours=2)
        db.add(subscription)
        db.commit()
        
        portal_url = f"{base_url}/portal/{subscription.id}?token={token}"
        return {
            "portal_url": portal_url,
            "expires_at": subscription.portal_token_expires_at.isoformat()
        }

    @staticmethod
    def schedule_plan_change(db: Session, subscription: Subscription, plan_id: str | None) -> dict:
        """Schedule a subscription plan switch or cancel any pending schedule."""
        if not plan_id:
            subscription.pending_plan_id = None
            db.add(subscription)
            db.commit()
            return {"status": "cleared", "message": "Pending plan switch cancelled"}
            
        new_plan = db.query(Plan).filter(Plan.id == plan_id, Plan.project_id == subscription.project_id, Plan.is_active == True).first()
        if not new_plan:
            raise ValueError("Selected plan not found or inactive")
            
        if plan_id == subscription.plan_id:
            subscription.pending_plan_id = None
            db.add(subscription)
            db.commit()
            return {"status": "cleared", "message": "Pending plan switch cancelled"}
            
        subscription.pending_plan_id = plan_id
        db.add(subscription)
        db.commit()
        return {
            "status": "scheduled",
            "pending_plan_name": new_plan.name,
            "message": f"Subscription plan switch to {new_plan.name} scheduled for end of period."
        }

