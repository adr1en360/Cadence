import threading
import json
from datetime import datetime
import httpx
from app.core.security import sign_outbound_webhook

def _send_request(url: str, payload: dict, headers: dict):
    try:
        # Send post request synchronously in a background thread to prevent blocking
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=payload, headers=headers)
            print(f"[WEBHOOK DISPATCH] Sent webhook to {url}. Status: {response.status_code}")
    except Exception as e:
        print(f"[WEBHOOK DISPATCH] Failed to send webhook to {url}: {e}")

def dispatch_webhook(project, event_type: str, data: dict):
    """
    Asynchronously dispatch a webhook payload to the project's configured webhook_url.
    Runs in a background thread to avoid blocking database transactions or API responses.
    """
    if not project or not project.webhook_url:
        return
        
    payload = {
        "event_type": event_type,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "data": data
    }
    
    headers = {
        "Content-Type": "application/json",
    }
    
    if project.webhook_secret:
        # Sign the webhook payload
        signature = sign_outbound_webhook(payload, project.webhook_secret)
        headers["X-Cadence-Signature"] = signature
        
    # Dispatch using a background thread
    thread = threading.Thread(
        target=_send_request,
        args=(project.webhook_url, payload, headers),
        daemon=True
    )
    thread.start()
