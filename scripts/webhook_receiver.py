"""
Nomba Webhook Receiver — tokenKey Discovery Test
Runs a simple HTTP server that logs ALL incoming requests to find where tokenKey lives.
"""
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

LOG_FILE = "webhook_payloads.json"
PORT = 8000


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # Parse the payload
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {"raw": body.decode("utf-8", errors="replace")}

        # Capture everything
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "path": self.path,
            "method": "POST",
            "headers": dict(self.headers),
            "payload": payload,
        }

        # Pretty-print to console
        print("\n" + "=" * 80)
        print(f"[WEBHOOK RECEIVED] at {entry['timestamp']}")
        print(f"   Path: {self.path}")
        print(f"   Headers:")
        for k, v in self.headers.items():
            print(f"     {k}: {v}")
        print(f"   Payload:")
        print(json.dumps(payload, indent=2))
        print("=" * 80)

        # Search for tokenKey recursively
        token_key_locations = []
        _find_key(payload, "tokenKey", "", token_key_locations)
        _find_key(payload, "token_key", "", token_key_locations)
        _find_key(payload, "tokenkey", "", token_key_locations)
        _find_key(payload, "card_token", "", token_key_locations)
        _find_key(payload, "cardToken", "", token_key_locations)

        if token_key_locations:
            print("\n>>> TOKEN KEY FOUND! <<<")
            for loc in token_key_locations:
                print(f"   Location: {loc}")
        else:
            print("\n[!] No tokenKey/token_key/cardToken found in this payload.")
            print("   This might be a non-tokenized payment event.")

        # Append to log file
        log = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                try:
                    log = json.load(f)
                except json.JSONDecodeError:
                    log = []
        log.append(entry)
        with open(LOG_FILE, "w") as f:
            json.dump(log, f, indent=2)

        # Respond 200 OK
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "received"}).encode())

    def do_GET(self):
        """Health check / browser visit"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = """
        <html><body style="font-family:monospace;background:#111;color:#0f0;padding:40px">
        <h1>Cadence Webhook Receiver</h1>
        <p>Listening for Nomba webhooks on port {port}...</p>
        <p>POST payloads are logged to <code>webhook_payloads.json</code></p>
        </body></html>
        """.format(port=PORT)
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default access logs to keep output clean"""
        pass


def _find_key(obj, target_key, path, results):
    """Recursively search for a key in nested dicts/lists"""
    target_lower = target_key.lower()
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if k.lower() == target_lower:
                results.append(f"{current_path} = {v}")
            _find_key(v, target_key, current_path, results)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _find_key(item, target_key, f"{path}[{i}]", results)


if __name__ == "__main__":
    print(f"[*] Cadence Webhook Receiver starting on port {PORT}")
    print(f"    Logging all payloads to {LOG_FILE}")
    print(f"    Searching for: tokenKey, token_key, cardToken, card_token")
    print(f"")
    print(f"    Next steps:")
    print(f"    1. Run: ngrok http {PORT}")
    print(f"    2. Copy the ngrok HTTPS URL")
    print(f"    3. Create a Nomba sandbox checkout with that URL as callbackUrl")
    print(f"    4. Complete payment with card 5434621074252808, OTP 9999")
    print(f"    5. Watch this terminal for the webhook payload")
    print(f"")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    server.serve_forever()
