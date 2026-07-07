import httpx
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings

class NombaClient:
    def __init__(self):
        self.base_url = "https://sandbox.nomba.com" if settings.NOMBA_ENV == "sandbox" else "https://api.nomba.com"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

    async def get_token_for_project(self, db: Session, project) -> str:
        """Retrieve token, utilizing database-cached token if valid, otherwise fetch and save."""
        # 1. Check if we have dynamic project credentials
        client_id = project.nomba_client_id
        client_secret = project.nomba_client_secret_encrypted
        account_id = project.nomba_account_id
        
        if client_secret:
            from app.core.security import decrypt_credential
            try:
                client_secret = decrypt_credential(client_secret)
            except Exception as e:
                # Fallback if secret was stored as plaintext in DB
                print(f"[NOMBA] Decryption failed for client secret (using as plaintext): {e}")
        
        # Fallback to default credentials if not configured on project (e.g. for default sandbox runs)
        if not client_id or not client_secret or not account_id:
            client_id = settings.NOMBA_CLIENT_ID
            client_secret = settings.NOMBA_CLIENT_SECRET
            account_id = settings.NOMBA_ACCOUNT_ID
            
        if not client_id or not client_secret or not account_id:
            raise ValueError(f"Nomba credentials not configured for project: {project.name}")

        # 2. Check if DB cached token is valid (with 5 min grace period for expiry)
        if (project.nomba_access_token and 
                project.nomba_token_expires_at and 
                datetime.utcnow() + timedelta(minutes=5) < project.nomba_token_expires_at):
            return project.nomba_access_token

        # 3. Fetch new token from Nomba
        url = f"{self.base_url}/v1/auth/token/issue"
        headers = {
            "Content-Type": "application/json",
            "accountId": account_id,
            "User-Agent": self.ua,
        }
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()["data"]
            
            # Update DB cache
            project.nomba_access_token = data["access_token"]
            project.nomba_token_expires_at = datetime.utcnow() + timedelta(minutes=30)
            db.add(project)
            db.commit()
            
            return project.nomba_access_token

    async def _get_auth_headers_for_project(self, db: Session, project, idempotency_key: str = None) -> dict:
        """Generate request headers with authorization for the given project."""
        token = await self.get_token_for_project(db, project)
        account_id = project.nomba_account_id or settings.NOMBA_ACCOUNT_ID
        
        headers = {
            "Authorization": f"Bearer {token}",
            "accountId": account_id,
            "Content-Type": "application/json",
            "User-Agent": self.ua,
        }
        if idempotency_key:
            headers["X-Idempotent-key"] = idempotency_key
        return headers

    async def create_checkout_order(
        self,
        db: Session,
        project,
        order_ref: str,
        amount: float,
        customer_email: str,
        callback_url: str,
        currency: str = "NGN",
        sub_account_id: str = None
    ) -> dict:
        """Create a checkout order with tokenizeCard=True to capture tokenKey."""
        path = "/v1/checkout/order"
        url = f"{self.base_url}{path}"
        
        order_payload = {
            "orderReference": order_ref,
            "amount": f"{amount:.2f}",
            "currency": currency,
            "customerEmail": customer_email,
            "callbackUrl": callback_url,
        }
        if sub_account_id:
            order_payload["accountId"] = sub_account_id
            
        payload = {
            "order": order_payload,
            "tokenizeCard": True,
            "allowedPaymentMethods": ["Card"],
        }
        
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def charge_tokenized_card(
        self,
        db: Session,
        project,
        token_key: str,
        order_ref: str,
        amount: float,
        idempotency_key: str,
        currency: str = "NGN",
        sub_account_id: str = None
    ) -> dict:
        """Charge a saved card using its tokenKey (Tokenized Card Payment)."""
        if not token_key:
            raise ValueError("token_key cannot be null or empty for tokenized card charges")
            
        url = f"{self.base_url}/v1/checkout/tokenized-card-payment"
        
        order_payload = {
            "orderReference": order_ref,
            "amount": f"{amount:.2f}",
            "currency": currency,
        }
        if sub_account_id:
            order_payload["accountId"] = sub_account_id
            
        payload = {
            "tokenKey": token_key,
            "order": order_payload
        }
        
        headers = await self._get_auth_headers_for_project(db, project, idempotency_key=idempotency_key)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def verify_transaction(self, db: Session, project, order_ref: str) -> dict:
        """Verify the status of a checkout transaction."""
        path = "/v1/checkout/transaction"
        url = f"{self.base_url}{path}"
        params = {
            "idType": "orderReference",
            "id": order_ref
        }
        
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def refund_transaction(self, db: Session, project, transaction_id: str, amount: float) -> dict:
        """Refund a completed transaction."""
        path = "/v1/checkout/refund"
        url = f"{self.base_url}{path}"
        payload = {
            "transactionId": transaction_id,
            "amount": amount
        }
        
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_tokenized_cards(self, db: Session, project, customer_email: str) -> dict:
        """Fetch tokenized card details for a customer email."""
        path = "/v1/checkout/tokenized-card-data"
        url = f"{self.base_url}{path}"
        params = {"customerEmail": customer_email}
        
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def delete_tokenized_card(self, db: Session, project, token_key: str) -> dict:
        """Delete tokenized card data from Nomba."""
        if not token_key:
            raise ValueError("token_key cannot be null or empty")
            
        path = "/v1/checkout/tokenized-card-data"
        url = f"{self.base_url}{path}"
        payload = {
            "tokenKey": token_key
        }
        
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.request("DELETE", url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_wallet_balance(self, db: Session, project, sub_account_id: str = None) -> dict:
        """Fetch balance from Nomba for parent account or sub-account."""
        if sub_account_id:
            url = f"{self.base_url}/v1/accounts/{sub_account_id}/balance"
        else:
            url = f"{self.base_url}/v1/accounts/balance"
            
        headers = await self._get_auth_headers_for_project(db, project)
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()["data"]

nomba_client = NombaClient()
