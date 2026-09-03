import concurrent.futures
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("API_URL", "http://api:8000")


def buy():
    body = json.dumps({"customer_id": "cora-17", "amount_cents": 7500}).encode()
    request = urllib.request.Request(BASE + "/buy", data=body, method="POST", headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main():
    reset = urllib.request.Request(BASE + "/_reset", data=b"", method="POST")
    urllib.request.urlopen(reset).read()
    body = json.dumps({"reproduce": True}).encode()
    control = urllib.request.Request(BASE + "/_control", data=body, method="POST", headers={"content-type": "application/json"})
    urllib.request.urlopen(control).read()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: buy(), range(2)))
    with urllib.request.urlopen(BASE + "/metrics") as response:
        metrics = json.load(response)
    print(json.dumps({"statuses": statuses, **metrics}))


if __name__ == "__main__":
    main()
