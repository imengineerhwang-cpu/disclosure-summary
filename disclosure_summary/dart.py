from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterator

import requests

from .config import get_dart_api_key

DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
DART_VIEWER_URL = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

CORP_CLS_LABEL = {"Y": "유가증권", "K": "코스닥", "N": "코넥스", "E": "기타"}


@dataclass
class Disclosure:
    rcept_no: str
    corp_code: str
    corp_name: str
    stock_code: str
    corp_cls: str
    report_nm: str
    flr_nm: str
    rcept_dt: str
    rm: str
    rcept_time: str = ""

    @property
    def viewer_url(self) -> str:
        return DART_VIEWER_URL.format(rcept_no=self.rcept_no)

    @property
    def market_label(self) -> str:
        return CORP_CLS_LABEL.get(self.corp_cls, self.corp_cls or "-")


class DartError(RuntimeError):
    pass


def _yyyymmdd(d: date) -> str:
    return d.strftime("%Y%m%d")


def fetch_disclosures(
    target_date: date,
    *,
    corp_cls: str | None = None,
    page_count: int = 100,
    timeout: float = 10.0,
) -> list[Disclosure]:
    """DART 공시검색 API로 특정 일자의 전체 공시를 가져온다."""
    api_key = get_dart_api_key()
    bgn = end = _yyyymmdd(target_date)

    out: list[Disclosure] = []
    for item in _paginate(api_key, bgn, end, corp_cls, page_count, timeout):
        out.append(
            Disclosure(
                rcept_no=item.get("rcept_no", ""),
                corp_code=item.get("corp_code", ""),
                corp_name=item.get("corp_name", ""),
                stock_code=item.get("stock_code", "") or "",
                corp_cls=item.get("corp_cls", ""),
                report_nm=item.get("report_nm", ""),
                flr_nm=item.get("flr_nm", ""),
                rcept_dt=item.get("rcept_dt", ""),
                rm=item.get("rm", "") or "",
            )
        )
    return out


def _paginate(
    api_key: str,
    bgn: str,
    end: str,
    corp_cls: str | None,
    page_count: int,
    timeout: float,
) -> Iterator[dict]:
    page_no = 1
    while True:
        params = {
            "crtfc_key": api_key,
            "bgn_de": bgn,
            "end_de": end,
            "page_no": page_no,
            "page_count": page_count,
        }
        if corp_cls:
            params["corp_cls"] = corp_cls

        resp = requests.get(DART_LIST_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        body = resp.json()

        status = body.get("status")
        if status == "013":
            return
        if status != "000":
            raise DartError(
                f"DART API 오류: status={status} message={body.get('message')}"
            )

        for item in body.get("list", []):
            yield item

        total_page = int(body.get("total_page", 1) or 1)
        if page_no >= total_page:
            return
        page_no += 1
