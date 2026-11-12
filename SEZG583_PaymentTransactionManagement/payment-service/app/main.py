from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
import os
import sqlite3
import uuid

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.getenv("DB_PATH", "payments.db")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                merchant_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,
                transaction_id TEXT,
                created_at TEXT NOT NULL
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Payment Service",
    description="Academic simulation only. No real payment processing.",
    version="1.0.0",
    lifespan=lifespan,
)


class PaymentRequest(BaseModel):
    merchant_id: str = Field(min_length=3, max_length=64)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: str = Field(pattern="^TEST_CARD$")
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("currency")
    @classmethod
    def uppercase_currency(cls, value):
        value = value.upper()
        if value != "INR":
            raise ValueError("This demo supports INR only")
        return value


@app.get("/health")
def health():
    return {"service": "payment-service", "status": "ok"}


@app.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(request: PaymentRequest):
    with connect_db() as conn:
        existing = conn.execute(
            "SELECT * FROM payments WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing:
            return dict(existing)

    # Deterministic classroom rule, not real authorization:
    # amounts <= INR 10,000 are approved; higher amounts are declined.
    payment_status = "AUTHORIZED" if request.amount <= Decimal("10000.00") else "DECLINED"
    payment_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "payment_id": payment_id,
        "amount": str(request.amount.quantize(Decimal("0.01"))),
        "currency": request.currency,
        "status": payment_status,
        "created_at": created_at,
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(f"{TRANSACTION_SERVICE_URL}/transactions", json=payload)
            response.raise_for_status()
            transaction = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Transaction Service unavailable; payment result was not saved. Retry with the same idempotency key.",
        ) from exc

    try:
        with connect_db() as conn:
            conn.execute(
                """INSERT INTO payments
                (payment_id, merchant_id, amount, currency, payment_method,
                 idempotency_key, status, transaction_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    payment_id, request.merchant_id, str(request.amount.quantize(Decimal("0.01"))),
                    request.currency, request.payment_method, request.idempotency_key,
                    payment_status, transaction["transaction_id"], created_at,
                ),
            )
    except sqlite3.IntegrityError:
        with connect_db() as conn:
            existing = conn.execute(
                "SELECT * FROM payments WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if existing:
                return dict(existing)
        raise HTTPException(status_code=409, detail="Duplicate idempotency key")

    return {
        "payment_id": payment_id,
        "transaction_id": transaction["transaction_id"],
        "merchant_id": request.merchant_id,
        "amount": str(request.amount.quantize(Decimal("0.01"))),
        "currency": request.currency,
        "status": payment_status,
        "message": "Simulated authorization result; no real payment was processed",
        "created_at": created_at,
    }


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return dict(row)
