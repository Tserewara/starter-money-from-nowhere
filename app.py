import json
import os
import threading
import time
import urllib.request
import uuid

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL")
PSP_URL = os.environ.get("PSP_URL", "http://localhost:8001")
barrier = threading.Barrier(2)
log_lock = threading.Lock()
request_log = []
psp_state = {"latency_ms": 150, "fail": False}
psp_lock = threading.Lock()
reproduce_race = False


def connect():
    return psycopg.connect(DATABASE_URL)


def init_db():
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS wallets (customer_id text primary key, balance_cents integer not null)")
                conn.execute("CREATE TABLE IF NOT EXISTS purchases (purchase_id text primary key, customer_id text not null, amount_cents integer not null, request_id text not null)")
                conn.execute("INSERT INTO wallets VALUES ('cora-17', 10000) ON CONFLICT DO NOTHING")
                conn.commit()
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise RuntimeError("database did not become ready")


def record(entry):
    with log_lock:
        request_log.append(entry)
        del request_log[:-200]
    print(json.dumps(entry), flush=True)


class BuyRequest(BaseModel):
    customer_id: str = "cora-17"
    amount_cents: int = 7500


api_app = FastAPI(title="Hearth wallet")
psp_app = FastAPI(title="Fake payment service provider")


@api_app.on_event("startup")
def startup():
    init_db()


@api_app.get("/health")
def health():
    return {"ok": True}


@api_app.post("/buy")
def buy(payload: BuyRequest):
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    with connect() as conn:
        with conn.transaction():
            row = conn.execute("SELECT balance_cents FROM wallets WHERE customer_id = %s", (payload.customer_id,)).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="wallet not found")
            observed = row[0]
            record({"event": "balance_read", "request_id": request_id, "customer_id": payload.customer_id, "balance_cents": observed})
            if reproduce_race:
                try:
                    barrier.wait(timeout=5)
                except threading.BrokenBarrierError:
                    pass
            lock_started = time.perf_counter()
            conn.execute("SELECT balance_cents FROM wallets WHERE customer_id = %s FOR UPDATE", (payload.customer_id,)).fetchone()
            lock_wait_ms = round((time.perf_counter() - lock_started) * 1000, 1)
            record({"event": "wallet_lock", "request_id": request_id, "lock_wait_ms": lock_wait_ms})
            if observed < payload.amount_cents:
                raise HTTPException(status_code=409, detail="insufficient funds")
            psp_request(request_id, payload.amount_cents)
            conn.execute("UPDATE wallets SET balance_cents = balance_cents - %s WHERE customer_id = %s", (payload.amount_cents, payload.customer_id))
            conn.execute("INSERT INTO purchases VALUES (%s, %s, %s, %s)", (str(uuid.uuid4()), payload.customer_id, payload.amount_cents, request_id))
    return {"ok": True, "request_id": request_id, "elapsed_ms": round((time.perf_counter() - started) * 1000, 1)}


def psp_request(request_id, amount_cents):
    payload = json.dumps({"request_id": request_id, "amount_cents": amount_cents}).encode()
    request = urllib.request.Request(PSP_URL + "/charge", data=payload, method="POST", headers={"content-type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


@api_app.get("/wallets")
def wallets():
    with connect() as conn:
        rows = conn.execute("SELECT customer_id, balance_cents FROM wallets ORDER BY customer_id").fetchall()
    return {"wallets": [{"customer_id": row[0], "balance_cents": row[1]} for row in rows]}


@api_app.get("/evidence")
def evidence():
    with log_lock:
        return {"events": list(request_log)}


@api_app.get("/metrics")
def metrics():
    with connect() as conn:
        negative = conn.execute("SELECT count(*) FROM wallets WHERE balance_cents < 0").fetchone()[0]
        purchases = conn.execute("SELECT count(*) FROM purchases").fetchone()[0]
    with log_lock:
        waits = sorted([event["lock_wait_ms"] for event in request_log if event["event"] == "wallet_lock"])
    p99 = waits[min(len(waits) - 1, int(len(waits) * 0.99))] if waits else 0
    return {"negative_balances": negative, "purchase_count": purchases, "lock_wait_p99_ms": p99, "psp_latency_ms": psp_state["latency_ms"]}


@api_app.post("/_reset")
def reset():
    global reproduce_race
    with connect() as conn:
        conn.execute("TRUNCATE purchases")
        conn.execute("UPDATE wallets SET balance_cents = 10000 WHERE customer_id = 'cora-17'")
        conn.commit()
    with log_lock:
        request_log.clear()
    reproduce_race = False
    return {"ok": True}


@api_app.post("/_control")
def control(payload: dict):
    global reproduce_race
    reproduce_race = bool(payload.get("reproduce", reproduce_race))
    return {"reproduce": reproduce_race}


@psp_app.post("/_control")
def psp_control(payload: dict):
    with psp_lock:
        if "latency_ms" in payload:
            psp_state["latency_ms"] = int(payload["latency_ms"])
        if "fail" in payload:
            psp_state["fail"] = bool(payload["fail"])
    return psp_state


@psp_app.post("/charge")
def charge(_: dict):
    with psp_lock:
        latency_ms = psp_state["latency_ms"]
        fail = psp_state["fail"]
    time.sleep(latency_ms / 1000)
    if fail:
        raise HTTPException(status_code=503, detail="PSP unavailable")
    return {"approved": True}
