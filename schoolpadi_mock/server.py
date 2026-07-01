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
        "api_key": ""
    }

def save_config(config_data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f)

class ConfigPayload(BaseModel):
    cadence_api_url: str
    api_key: str

class SubscribePayload(BaseModel):
    plan_id: str
    customer_email: str
    customer_name: str

@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/config")
def get_config():
    return load_config()

@app.post("/api/config")
def update_config(payload: ConfigPayload):
    config = {
        "cadence_api_url": payload.cadence_api_url.rstrip("/"),
        "api_key": payload.api_key.strip()
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
    body = {
        "plan_id": payload.plan_id,
        "customer_email": payload.customer_email,
        "customer_name": payload.customer_name,
        "callback_url": f"http://localhost:8001/checkout-success"  # Redirect back to SchoolPadi after Nomba pay
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
