from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import sqlite3
import uuid

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "transactions.db")


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                payment_id TEXT NOT NULL UNIQUE,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Transaction Service",
    description="Stores synthetic transaction records for the academic demo.",
    version="1.0.0",
    lifespan=lifespan,
)


class TransactionCreate(BaseModel):
    payment_id: str = Field(min_length=1, max_length=64)
    amount: str = Field(pattern=r"^\d{1,10}\.\d{2}$")
    currency: str = Field(pattern="^INR$")
    status: str = Field(pattern="^(AUTHORIZED|DECLINED)$")
    created_at: str


@app.get("/health")
def health():
    return {"service": "transaction-service", "status": "ok"}


@app.post("/transactions", status_code=201)
def create_transaction(request: TransactionCreate):
    with connect_db() as conn:
        existing = conn.execute(
            "SELECT * FROM transactions WHERE payment_id = ?", (request.payment_id,)
        ).fetchone()
        if existing:
            return dict(existing)
        transaction_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO transactions
            (transaction_id, payment_id, amount, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                transaction_id, request.payment_id, request.amount,
                request.currency, request.status, request.created_at or datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
    return dict(row)


@app.get("/transactions")
def list_transactions(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    with connect_db() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "limit": limit, "offset": offset}


@app.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    with connect_db() as conn:
        row = conn.execute(
            "SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return dict(row)
