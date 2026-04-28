"""주가 데이터 수집·저장.

FinanceDataReader의 `StockListing("KRX")` 호출 한 번으로
전 종목 현재 스냅샷(종가·등락률·거래량 등)을 받아온다.
스냅샷은 시점(현재) 기반이므로, 장 마감 후 실행하면 당일 종가가 된다.
장 중 실행하면 실시간 가격이 들어가니 보통 8시 이후에 fetch 권장.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass
class Price:
    stock_code: str
    date: str
    close: float | None
    change_amount: float | None
    change_rate: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: int | None
    market_cap: int | None


def _safe_float(v) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        return f if f == f else None  # NaN check
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def fetch_prices(target_date: date) -> list[Price]:
    import FinanceDataReader as fdr

    yyyymmdd = target_date.strftime("%Y%m%d")
    df = fdr.StockListing("KRX")

    # FinanceDataReader 0.9.x 에서는 "ChagesRatio" 오타가 있음. 둘 다 처리.
    rate_col = "ChangesRatio" if "ChangesRatio" in df.columns else "ChagesRatio"

    out: list[Price] = []
    for _, row in df.iterrows():
        code = str(row.get("Code", "")).strip()
        if not code:
            continue
        out.append(
            Price(
                stock_code=code,
                date=yyyymmdd,
                close=_safe_float(row.get("Close")),
                change_amount=_safe_float(row.get("Changes")),
                change_rate=_safe_float(row.get(rate_col)),
                open=_safe_float(row.get("Open")),
                high=_safe_float(row.get("High")),
                low=_safe_float(row.get("Low")),
                volume=_safe_int(row.get("Volume")),
                market_cap=_safe_int(row.get("Marcap")),
            )
        )
    return out


PRICES_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    stock_code    TEXT NOT NULL,
    date          TEXT NOT NULL,
    close         REAL,
    change_amount REAL,
    change_rate   REAL,
    open          REAL,
    high          REAL,
    low           REAL,
    volume        INTEGER,
    market_cap    INTEGER,
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (stock_code, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
"""


def upsert_prices(conn: sqlite3.Connection, items: Iterable[Price]) -> int:
    rows = [
        (
            p.stock_code,
            p.date,
            p.close,
            p.change_amount,
            p.change_rate,
            p.open,
            p.high,
            p.low,
            p.volume,
            p.market_cap,
        )
        for p in items
    ]
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT INTO prices
            (stock_code, date, close, change_amount, change_rate, open, high, low, volume, market_cap)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(stock_code, date) DO UPDATE SET
            close = excluded.close,
            change_amount = excluded.change_amount,
            change_rate = excluded.change_rate,
            open = excluded.open,
            high = excluded.high,
            low = excluded.low,
            volume = excluded.volume,
            market_cap = excluded.market_cap
        """,
        rows,
    )
    return len(rows)


def load_prices_map(conn: sqlite3.Connection, target_date: date) -> dict[str, Price]:
    """Return {stock_code: Price} for the given date."""
    yyyymmdd = target_date.strftime("%Y%m%d")
    cur = conn.execute(
        """
        SELECT stock_code, date, close, change_amount, change_rate,
               open, high, low, volume, market_cap
        FROM prices
        WHERE date = ?
        """,
        (yyyymmdd,),
    )
    out: dict[str, Price] = {}
    for row in cur.fetchall():
        p = Price(
            stock_code=row[0],
            date=row[1],
            close=row[2],
            change_amount=row[3],
            change_rate=row[4],
            open=row[5],
            high=row[6],
            low=row[7],
            volume=row[8],
            market_cap=row[9],
        )
        out[p.stock_code] = p
    return out
