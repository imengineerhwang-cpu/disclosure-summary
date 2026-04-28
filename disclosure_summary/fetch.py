from __future__ import annotations

import argparse
from datetime import date, datetime

from .dart import fetch_disclosures
from .dart_times import fetch_times_for_date
from .db import connect, update_rcept_times, upsert_disclosures
from .prices import fetch_prices, upsert_prices


def parse_date(s: str | None) -> date:
    if not s:
        return date.today()
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="DART 일별 공시 + 주가 수집")
    parser.add_argument("--date", help="대상 일자 (YYYY-MM-DD). 생략 시 오늘.")
    parser.add_argument(
        "--corp-cls",
        choices=["Y", "K", "N", "E"],
        help="시장 필터 (Y=유가증권, K=코스닥, N=코넥스, E=기타). 생략 시 전체.",
    )
    parser.add_argument(
        "--no-prices", action="store_true", help="주가 스냅샷 수집 생략"
    )
    parser.add_argument(
        "--no-times", action="store_true", help="공시 시각(HH:MM) 스크래핑 생략"
    )
    args = parser.parse_args()

    target = parse_date(args.date)
    print(f"[fetch] {target} 공시 조회 중...")
    items = fetch_disclosures(target, corp_cls=args.corp_cls)
    print(f"[fetch] DART에서 {len(items)}건 수신")

    with connect() as conn:
        n = upsert_disclosures(conn, items)
        print(f"[fetch] 공시 DB에 {n}건 저장 완료")

        if not args.no_times:
            print(f"[fetch] {target} 공시 시각 스크래핑 중...")
            try:
                time_map = fetch_times_for_date(target)
                tn = update_rcept_times(conn, time_map)
                print(f"[fetch] 시각 정보 {tn}건 갱신 (대상 {len(time_map)}건)")
            except Exception as e:
                print(f"[fetch] 시각 수집 실패 (계속 진행): {e}")

        if not args.no_prices:
            print(f"[fetch] {target} 주가 스냅샷 조회 중...")
            try:
                prices = fetch_prices(target)
                pn = upsert_prices(conn, prices)
                print(f"[fetch] 주가 DB에 {pn}건 저장 완료")
            except Exception as e:
                print(f"[fetch] 주가 수집 실패 (계속 진행): {e}")


if __name__ == "__main__":
    main()
