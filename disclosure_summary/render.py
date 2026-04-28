from __future__ import annotations

import argparse
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .config import REPORTS_DIR, STATIC_DIR, TEMPLATES_DIR, ensure_dirs
from .dart import Disclosure
from .db import connect, load_disclosures_for_date
from .filters import apply_default_filters
from .prices import Price, load_prices_map
from .signals import (
    BUY_SIGNALS,
    SELL_SIGNALS,
    SIGNAL_CSS_CLASS,
    SIGNAL_ORDER,
    SIGNAL_RANK,
    classify,
)


@dataclass
class ScoredDisclosure:
    disclosure: Disclosure
    signal: str
    price: Price | None = None

    @property
    def signal_class(self) -> str:
        return SIGNAL_CSS_CLASS[self.signal]

    @property
    def change_class(self) -> str:
        if self.price is None or self.price.change_rate is None:
            return "na"
        r = self.price.change_rate
        if r > 0:
            return "up"
        if r < 0:
            return "down"
        return "flat"

    @property
    def change_rate_str(self) -> str:
        if self.price is None or self.price.change_rate is None:
            return "—"
        r = self.price.change_rate
        sign = "+" if r > 0 else ""
        return f"{sign}{r:.2f}%"

    @property
    def close_str(self) -> str:
        if self.price is None or self.price.close is None:
            return ""
        c = self.price.close
        return f"{int(c):,}" if c >= 1 else f"{c:,.2f}"

    @property
    def signal_rank(self) -> int:
        return SIGNAL_RANK.get(self.signal, 0)

    @property
    def time_sort_key(self) -> str:
        return self.disclosure.rcept_time or "00:00"

    @property
    def rate_sort_key(self) -> float:
        if self.price is None or self.price.change_rate is None:
            return -9999.0
        return self.price.change_rate

    @property
    def cap_sort_key(self) -> int:
        if self.price is None or self.price.market_cap is None:
            return 0
        return self.price.market_cap

    @property
    def market_cap_str(self) -> str:
        if self.price is None or self.price.market_cap is None:
            return ""
        mc = self.price.market_cap
        if mc <= 0:
            return ""
        EOK = 100_000_000  # 1억
        JO = 10_000 * EOK  # 1조
        if mc >= JO:
            jo_part = mc // JO
            eok_part = (mc % JO) // EOK
            return f"{jo_part:,}조 {eok_part:,}억" if eok_part else f"{jo_part:,}조"
        if mc >= EOK:
            return f"{mc // EOK:,}억"
        return f"{int(mc):,}"


@dataclass
class ReportContext:
    target_date: date
    rows: list[ScoredDisclosure] = field(default_factory=list)
    raw_count: int = 0

    @property
    def total_count(self) -> int:
        return len(self.rows)

    @property
    def unique_corps(self) -> int:
        return len({r.disclosure.corp_code for r in self.rows if r.disclosure.corp_code})

    @property
    def kospi_count(self) -> int:
        return sum(1 for r in self.rows if r.disclosure.corp_cls == "Y")

    @property
    def kosdaq_count(self) -> int:
        return sum(1 for r in self.rows if r.disclosure.corp_cls == "K")

    @property
    def signal_counts(self) -> dict[str, int]:
        c = Counter(r.signal for r in self.rows)
        return {s: c.get(s, 0) for s in SIGNAL_ORDER}

    @property
    def grouped_rows(self) -> list[list[ScoredDisclosure]]:
        """corp_code 단위로 묶은 그룹 리스트. 각 그룹은 시각 desc, 그룹 간은 최신 시각 desc."""
        groups: dict[str, list[ScoredDisclosure]] = {}
        for r in self.rows:
            key = r.disclosure.corp_code or r.disclosure.corp_name
            groups.setdefault(key, []).append(r)
        for g in groups.values():
            g.sort(key=lambda x: x.time_sort_key, reverse=True)
        return sorted(
            groups.values(),
            key=lambda g: (g[0].time_sort_key, g[0].disclosure.rcept_no),
            reverse=True,
        )

    @property
    def buy_count(self) -> int:
        return sum(c for s, c in self.signal_counts.items() if s in BUY_SIGNALS)

    @property
    def sell_count(self) -> int:
        return sum(c for s, c in self.signal_counts.items() if s in SELL_SIGNALS)


def parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    return datetime.strptime(s, "%Y-%m-%d").date()


def render_report(
    target: date,
    output_dir: Path | None = None,
    *,
    apply_filters: bool = True,
) -> Path:
    with connect() as conn:
        all_items = load_disclosures_for_date(conn, target)
        prices = load_prices_map(conn, target)

    raw_count = len(all_items)
    items = apply_default_filters(all_items) if apply_filters else all_items
    rows = [
        ScoredDisclosure(
            disclosure=d,
            signal=classify(d),
            price=prices.get(d.stock_code) if d.stock_code else None,
        )
        for d in items
    ]

    ctx = ReportContext(target_date=target, rows=rows, raw_count=raw_count)

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("report.html")
    html = template.render(ctx=ctx, generated_at=datetime.now())

    out_dir = output_dir or (REPORTS_DIR / target.strftime("%Y-%m-%d"))
    out_dir.mkdir(parents=True, exist_ok=True)

    for asset in ("style.css", "report.js"):
        src = STATIC_DIR / asset
        if src.exists():
            shutil.copy(src, out_dir / asset)

    out_path = out_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="공시 일일 리포트 HTML 생성")
    parser.add_argument("--date", help="대상 일자 (YYYY-MM-DD). 생략 시 오늘.")
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="기본 필터(코넥스/기타법인/펀드공시 제외) 비활성화",
    )
    args = parser.parse_args()

    ensure_dirs()
    target = parse_date(args.date)
    out_path = render_report(target, apply_filters=not args.no_filter)
    print(f"[render] 리포트 생성 완료 -> {out_path}")


if __name__ == "__main__":
    main()
