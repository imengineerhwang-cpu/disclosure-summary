"""DART '최근공시' 페이지에서 공시별 시:분 정보를 스크래핑.

OpenAPI list.json 은 날짜만 주기 때문에, 시간 정보는 dart.fss.or.kr 의
최근공시 페이지(mainY/mainK)를 HTML 파싱해 보강한다.
페이지 구조 변경 시 깨질 수 있는 비공식 경로 — 깨지면 시간 컬럼만 비워지고
나머지 리포트는 정상 동작하도록 호출부에서 예외를 흡수한다.
"""

from __future__ import annotations

import re
import time as time_mod
from datetime import date

import requests

MARKET_URLS = {
    "Y": "https://dart.fss.or.kr/dsac001/mainY.do",   # 유가증권시장
    "K": "https://dart.fss.or.kr/dsac001/mainK.do",   # 코스닥시장
    "O": "https://dart.fss.or.kr/dsac001/mainO.do",   # 5%·임원보고 (시장 무관)
}

_TBODY_RE = re.compile(r"<tbody[^>]*>(.*?)</tbody>", re.DOTALL)
_TIME_RE = re.compile(r"<td>\s*(\d{2}:\d{2})\s*</td>")
_RCPT_RE = re.compile(r"rcpNo=(\d{14})")
_DATE_RE = re.compile(r"<td>\s*(\d{4}\.\d{2}\.\d{2})\s*</td>")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Referer": "https://dart.fss.or.kr/",
}


def fetch_times_for_date(
    target_date: date,
    *,
    markets: tuple[str, ...] = ("Y", "K", "O"),
    max_pages: int = 50,
    sleep_between: float = 0.1,
) -> dict[str, str]:
    """{rcept_no: 'HH:MM'} 매핑 반환. 실패 시 빈 dict."""
    target_dot = target_date.strftime("%Y.%m.%d")
    out: dict[str, str] = {}

    for market in markets:
        url = MARKET_URLS.get(market)
        if not url:
            continue
        for page in range(1, max_pages + 1):
            try:
                resp = requests.get(
                    url,
                    params={"currentPage": str(page), "selectDate": target_dot},
                    timeout=10,
                    headers=_HEADERS,
                )
            except requests.RequestException:
                break
            if resp.status_code != 200:
                break
            resp.encoding = "utf-8"
            tbody_m = _TBODY_RE.search(resp.text)
            if not tbody_m:
                break
            chunks = [c for c in tbody_m.group(1).split("</tr>") if c.strip()]
            if not chunks:
                break

            matched_in_page = 0
            for chunk in chunks:
                tm = _TIME_RE.search(chunk)
                rm = _RCPT_RE.search(chunk)
                dts = _DATE_RE.findall(chunk)
                if not (tm and rm and dts):
                    continue
                if dts[-1] != target_dot:
                    continue
                out[rm.group(1)] = tm.group(1)
                matched_in_page += 1

            if matched_in_page == 0:
                break
            if sleep_between:
                time_mod.sleep(sleep_between)

    return out
