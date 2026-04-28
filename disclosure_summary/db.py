from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterable, Iterator

from .config import DB_PATH, ensure_dirs
from .dart import Disclosure
from .prices import PRICES_SCHEMA

SCHEMA = """
CREATE TABLE IF NOT EXISTS disclosures (
    rcept_no   TEXT PRIMARY KEY,
    rcept_dt   TEXT NOT NULL,
    rcept_time TEXT,
    corp_code  TEXT NOT NULL,
    corp_name  TEXT NOT NULL,
    stock_code TEXT,
    corp_cls   TEXT,
    report_nm  TEXT NOT NULL,
    flr_nm     TEXT,
    rm         TEXT,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_disclosures_date ON disclosures(rcept_dt);
CREATE INDEX IF NOT EXISTS idx_disclosures_stock ON disclosures(stock_code);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """기존 DB에 누락된 컬럼이 있으면 추가."""
    cur = conn.execute("PRAGMA table_info(disclosures)")
    cols = {row[1] for row in cur.fetchall()}
    if "rcept_time" not in cols:
        conn.execute("ALTER TABLE disclosures ADD COLUMN rcept_time TEXT")


@contextmanager
def connect(path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        conn.executescript(PRICES_SCHEMA)
        _migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_disclosures(conn: sqlite3.Connection, items: Iterable[Disclosure]) -> int:
    rows = [
        (
            d.rcept_no,
            d.rcept_dt,
            d.corp_code,
            d.corp_name,
            d.stock_code,
            d.corp_cls,
            d.report_nm,
            d.flr_nm,
            d.rm,
        )
        for d in items
    ]
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT INTO disclosures
            (rcept_no, rcept_dt, corp_code, corp_name, stock_code, corp_cls, report_nm, flr_nm, rm)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(rcept_no) DO UPDATE SET
            corp_name = excluded.corp_name,
            stock_code = excluded.stock_code,
            corp_cls = excluded.corp_cls,
            report_nm = excluded.report_nm,
            flr_nm = excluded.flr_nm,
            rm = excluded.rm
        """,
        rows,
    )
    return len(rows)


def load_disclosures_for_date(conn: sqlite3.Connection, target_date: date) -> list[Disclosure]:
    yyyymmdd = target_date.strftime("%Y%m%d")
    cur = conn.execute(
        """
        SELECT rcept_no, corp_code, corp_name, stock_code, corp_cls,
               report_nm, flr_nm, rcept_dt, rcept_time, rm
        FROM disclosures
        WHERE rcept_dt = ?
        ORDER BY COALESCE(rcept_time, '00:00') DESC, rcept_no DESC
        """,
        (yyyymmdd,),
    )
    return [
        Disclosure(
            rcept_no=row["rcept_no"],
            corp_code=row["corp_code"],
            corp_name=row["corp_name"],
            stock_code=row["stock_code"] or "",
            corp_cls=row["corp_cls"] or "",
            report_nm=row["report_nm"],
            flr_nm=row["flr_nm"] or "",
            rcept_dt=row["rcept_dt"],
            rcept_time=row["rcept_time"] or "",
            rm=row["rm"] or "",
        )
        for row in cur.fetchall()
    ]


def update_rcept_times(conn: sqlite3.Connection, time_map: dict[str, str]) -> int:
    if not time_map:
        return 0
    rows = [(t, rcpt) for rcpt, t in time_map.items()]
    conn.executemany(
        "UPDATE disclosures SET rcept_time = ? WHERE rcept_no = ?", rows
    )
    return len(rows)
