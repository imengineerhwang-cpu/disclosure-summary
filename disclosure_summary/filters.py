from __future__ import annotations

from .dart import Disclosure

EXCLUDED_CORP_CLS = {"N", "E"}

FUND_NAME_KEYWORDS = (
    "펀드",
    "자산운용",
    "투자신탁",
    "투자회사",
    "유동화전문",
)


def is_fund_like(d: Disclosure) -> bool:
    text = (d.corp_name or "") + " " + (d.flr_nm or "")
    return any(kw in text for kw in FUND_NAME_KEYWORDS)


def is_excluded(d: Disclosure) -> bool:
    if d.corp_cls in EXCLUDED_CORP_CLS:
        return True
    if is_fund_like(d):
        return True
    return False


def apply_default_filters(items: list[Disclosure]) -> list[Disclosure]:
    """기본 제외: 코넥스(N), 기타법인(E), 펀드공시."""
    return [d for d in items if not is_excluded(d)]
