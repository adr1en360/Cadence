from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import os
import json

app = FastAPI(title="SchoolPadi Platform Mock")

# Simple local config storage
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "schoolpadi_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "cadence_api_url": "http://localhost:8000",
        "api_key": "",
        "webhook_secret": "",
        "callback_url": "http://localhost:8001/checkout-success",
        "webhook_url": "http://localhost:8001/api/webhook"
    }

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

class ConfigPayload(BaseModel):
    cadence_api_url: str
    api_key: str
    webhook_secret: str = ""
    callback_url: str = "http://localhost:8001/checkout-success"
    webhook_url: str = "http://localhost:8001/api/webhook"

class SubscribePayload(BaseModel):
    plan_id: str
    customer_email: str
    customer_name: str

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/checkout-success", response_class=HTMLResponse)
def checkout_success_page(request: Request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Successful - SchoolPadi</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@600;800&family=Sora:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {
                background: #090b10;
                color: #F3F4F6;
                font-family: 'Sora', sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
            }
            .card {
                background: rgba(17, 22, 32, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.075);
                border-radius: 22px;
                padding: 3rem;
                text-align: center;
                max-width: 450px;
                box-shadow: 0 24px 70px rgba(0, 0, 0, 0.36);
            }
            h1 {
                font-family: 'Outfit', sans-serif;
                font-size: 2rem;
                font-weight: 800;
                color: #10B981;
                margin-bottom: 1rem;
            }
            p {
                color: #9CA3AF;
                font-size: 0.95rem;
                line-height: 1.5;
                margin-bottom: 2rem;
            }
            .btn {
                background: linear-gradient(135deg, #FF6B00, #FF5100);
                color: white;
                padding: 0.8rem 1.8rem;
                border-radius: 10px;
                text-decoration: none;
                font-weight: 600;
                font-size: 0.9rem;
                display: inline-block;
                box-shadow: 0 12px 26px rgba(255, 107, 0, 0.18);
            }
            .icon {
                font-size: 4rem;
                margin-bottom: 1rem;
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <span class="icon">🎉</span>
            <h1>Payment Successful!</h1>
            <p>Your payment checkout has been completed. You can now close this tab and return to the SchoolPadi simulation hub to test webhook updates.</p>
            <a href="/" class="btn">Return to SchoolPadi</a>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(payload: ConfigPayload):
    config = {
        "cadence_api_url": payload.cadence_api_url.rstrip("/"),
        "api_key": payload.api_key.strip(),
        "webhook_secret": payload.webhook_secret.strip(),
        "callback_url": payload.callback_url.strip(),
        "webhook_url": payload.webhook_url.strip()
    }
    save_config(config)
    return {"status": "saved", "config": config}

@app.get("/api/plans")
async def get_plans():
    config = load_config()
    if not config["api_key"]:
        raise HTTPException(status_code=400, detail="API Key not configured in SchoolPadi settings")
        
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{config['cadence_api_url']}/api/plans", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Cadence: {str(e)}")

@app.post("/api/subscribe")
async def create_subscription(payload: SubscribePayload):
    config = load_config()
    if not config["api_key"]:
        raise HTTPException(status_code=400, detail="API Key not configured in SchoolPadi settings")
        
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    callback_url = config.get("callback_url") or "http://localhost:8001/checkout-success"
    body = {
        "plan_id": payload.plan_id,
        "customer_email": payload.customer_email,
        "customer_name": payload.customer_name,
        "callback_url": callback_url
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{config['cadence_api_url']}/api/subscriptions", headers=headers, json=body)
            if resp.status_code != 201:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Cadence: {str(e)}")

@app.get("/api/subscription/{sub_id}")
async def get_subscription(sub_id: str):
    config = load_config()
    if not config["api_key"]:
        raise HTTPException(status_code=400, detail="API Key not configured in SchoolPadi settings")
        
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{config['cadence_api_url']}/api/subscriptions/{sub_id}", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Cadence: {str(e)}")

@app.post("/api/subscription/{sub_id}/portal-link")
async def get_portal_link(sub_id: str):
    config = load_config()
    if not config["api_key"]:
        raise HTTPException(status_code=400, detail="API Key not configured in SchoolPadi settings")
        
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{config['cadence_api_url']}/api/subscriptions/{sub_id}/portal-link", headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Cadence: {str(e)}")

@app.post("/api/simulate-payment-success")
async def simulate_payment_success(payload: dict):
    config = load_config()
    # Call Cadence test webhook trigger directly
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{config['cadence_api_url']}/webhooks/test-success", json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to trigger test success webhook: {str(e)}")

@app.post("/api/simulate-payment-failed")
async def simulate_payment_failed(payload: dict):
    config = load_config()
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(f"{config['cadence_api_url']}/webhooks/test-failed", json=payload)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return resp.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to trigger test failed webhook: {str(e)}")

# Webhook storage and endpoints
webhook_events = []

@app.post("/api/webhook")
async def handle_cadence_webhook(request: Request):
    from datetime import datetime
    body = await request.body()
    headers = dict(request.headers)
    signature = headers.get("x-cadence-signature") or headers.get("X-Cadence-Signature")
    
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
        
    config = load_config()
    webhook_secret = config.get("webhook_secret", "")
    
    verified = None
    if webhook_secret and signature:
        import hmac
        import hashlib
        # Reconstruct compact JSON body (separators without spaces) as signed by Cadence
        compact_body = json.dumps(payload, separators=(',', ':'))
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            compact_body.encode("utf-8"),
            digestmod=hashlib.sha256
        ).hexdigest()
        verified = hmac.compare_digest(computed, signature)
        
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "payload": payload,
        "signature": signature,
        "verified": verified
    }
    
    webhook_events.append(entry)
    
    if len(webhook_events) > 50:
        webhook_events.pop(0)
        
    print(f"[SCHOOLPADI WEBHOOK] Received event: {payload.get('event_type')}. Signature verified: {verified}")
    return {"status": "received"}

@app.get("/api/webhooks")
def get_webhook_events():
    return webhook_events

@app.post("/api/webhooks/clear")
def clear_webhook_events():
    webhook_events.clear()
    return {"status": "cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
