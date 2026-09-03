import json
import os
import urllib.request

BASE = os.environ.get("API_URL", "http://api:8000")


def request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


request("POST", "/_reset")
result = request("POST", "/buy", {"customer_id": "cora-17", "amount_cents": 1000})
assert result["ok"] is True
wallet = request("GET", "/wallets")["wallets"][0]
assert wallet["balance_cents"] == 9000
print("2 tests passed")

