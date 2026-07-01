import httpx
from datetime import datetime, timedelta
from app.core.config import settings

class NombaClient:
    def __init__(self):
        self.base_url = "https://sandbox.nomba.com" if settings.NOMBA_ENV == "sandbox" else "https://api.nomba.com"
        self.client_id = settings.NOMBA_CLIENT_ID
        self.client_secret = settings.NOMBA_CLIENT_SECRET
        self.account_id = settings.NOMBA_ACCOUNT_ID
        self.sub_account_id = settings.NOMBA_SUB_ACCOUNT_ID
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        
        # In-memory token cache
        self._cached_token = None
        self._token_expires_at = None

    async def get_token(self) -> str:
        """Retrieve token, utilizing cached token if valid."""
        if self._cached_token and self._token_expires_at and datetime.utcnow() < self._token_expires_at:
            return self._cached_token

        url = f"{self.base_url}/v1/auth/token/issue"
        headers = {
            "Content-Type": "application/json",
            "accountId": self.account_id,
            "User-Agent": self.ua,
        }
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()["data"]
            self._cached_token = data["access_token"]
            # Proactively expire cached token 5 minutes early (typically 30m total lifetime)
            self._token_expires_at = datetime.utcnow() + timedelta(minutes=25)
            return self._cached_token

    async def _get_auth_headers(self, idempotency_key: str = None) -> dict:
        """Generate request headers with authorization."""
        token = await self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "accountId": self.account_id,
            "Content-Type": "application/json",
            "User-Agent": self.ua,
        }
        if idempotency_key:
            headers["X-Idempotent-key"] = idempotency_key
        return headers

    async def create_checkout_order(
        self,
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
        
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def charge_tokenized_card(
        self,
        token_key: str,
        order_ref: str,
        amount: float,
        idempotency_key: str,
        currency: str = "NGN",
        sub_account_id: str = None
    ) -> dict:
        """Charge a saved card using its tokenKey (Tokenized Card Payment)."""
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
        
        headers = await self._get_auth_headers(idempotency_key=idempotency_key)
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def verify_transaction(self, order_ref: str) -> dict:
        """Verify the status of a checkout transaction."""
        path = "/v1/checkout/transaction"
        url = f"{self.base_url}{path}"
        params = {
            "idType": "orderReference",
            "id": order_ref
        }
        
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def refund_transaction(self, transaction_id: str, amount: float) -> dict:
        """Refund a completed transaction."""
        path = "/v1/checkout/refund"
        url = f"{self.base_url}{path}"
        payload = {
            "transactionId": transaction_id,
            "amount": amount
        }
        
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def get_wallet_balance(self, sub_account_id: str = None) -> dict:
        """Fetch balance from Nomba for parent account or sub-account."""
        if sub_account_id:
            url = f"{self.base_url}/v1/accounts/{sub_account_id}/balance"
        else:
            url = f"{self.base_url}/v1/accounts/balance"
            
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()["data"]

nomba_client = NombaClient()
