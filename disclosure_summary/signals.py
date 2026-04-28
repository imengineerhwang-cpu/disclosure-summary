"""공시 유형(report_nm) 기반 룰 베이스 매매 시그널 분류.

본문 분석이 아니라 공시 제목만으로 판단하는 1차 분류이므로,
같은 카테고리 안에서도 실제 매매 임팩트는 크게 다를 수 있음.
Phase 4에서 본문/금액/매출 대비 비중을 고려한 정밀 분류로 보강 예정.
"""

from __future__ import annotations

from .dart import Disclosure

SIGNAL_AVOID = "회피"
SIGNAL_SELL = "매도"
SIGNAL_STRONG_BUY = "강매수"
SIGNAL_BUY = "매수"
SIGNAL_BUY_LEAN = "중립~매수"
SIGNAL_WATCH = "관망"
SIGNAL_NEUTRAL = "중립"

SIGNAL_ORDER = [
    SIGNAL_STRONG_BUY,
    SIGNAL_BUY,
    SIGNAL_BUY_LEAN,
    SIGNAL_NEUTRAL,
    SIGNAL_WATCH,
    SIGNAL_SELL,
    SIGNAL_AVOID,
]

SIGNAL_CSS_CLASS = {
    SIGNAL_STRONG_BUY: "strong-buy",
    SIGNAL_BUY: "buy",
    SIGNAL_BUY_LEAN: "buy-lean",
    SIGNAL_NEUTRAL: "neutral",
    SIGNAL_WATCH: "watch",
    SIGNAL_SELL: "sell",
    SIGNAL_AVOID: "avoid",
}

# 강도 순위 (정렬·집계용). 강매수=7 ~ 회피=1.
SIGNAL_RANK = {
    SIGNAL_STRONG_BUY: 7,
    SIGNAL_BUY: 6,
    SIGNAL_BUY_LEAN: 5,
    SIGNAL_NEUTRAL: 4,
    SIGNAL_WATCH: 3,
    SIGNAL_SELL: 2,
    SIGNAL_AVOID: 1,
}

BUY_SIGNALS = {SIGNAL_STRONG_BUY, SIGNAL_BUY, SIGNAL_BUY_LEAN}
SELL_SIGNALS = {SIGNAL_SELL, SIGNAL_AVOID}

# (signal, keywords) — 위에서부터 매칭, 첫 매칭 우선.
# 회피·매도 같은 부정 신호를 먼저 검사해 긍정 키워드와의 중복 매칭을 피한다.
SIGNAL_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        SIGNAL_AVOID,
        (
            "주권매매거래정지",
            "상장채권기한의이익상실",
            "소송등의제기",
            "중대재해",
            "투자판단관련주요경영사항",
            "횡령",
            "배임",
            "부도발생",
            "회생절차",
            "영업정지",
            "관리종목",
            "상장폐지",
            "감사의견거절",
            "감사의견부적정",
            "감사범위제한",
        ),
    ),
    (
        SIGNAL_SELL,
        (
            "유상증자결정",
            "전환사채권발행결정",
            "전환사채발행결정",
            "신주인수권부사채",
            "교환사채권발행결정",
            "교환사채발행결정",
            "전환청구권행사",
            "신주인수권행사",
            "감자결정",
            "감자완료",
            "자기주식처분결정",
            "타인에대한채무보증",
        ),
    ),
    (
        SIGNAL_STRONG_BUY,
        (
            "주식소각결정",
            "자기주식취득결정",
            "자기주식취득신탁계약체결결정",
            "무상증자결정",
        ),
    ),
    (
        SIGNAL_BUY,
        (
            "단일판매",
            "공급계약체결",
            "신규시설투자",
            "현금배당결정",
            "현물배당결정",
            "현금ㆍ현물배당결정",
            "기업가치제고계획",
            "영업양수",
            "합병결정",
            "기술이전",
            "주권매매거래정지해제",
            "투자유치",
            "수주공시",
        ),
    ),
    (
        SIGNAL_BUY_LEAN,
        (
            "기업설명회",
            "IR개최",
            "자기주식취득신탁계약해지",
        ),
    ),
    (
        SIGNAL_WATCH,
        (
            "대표이사변경",
            "대표이사의변경",
            "사외이사의선임",
            "주식분할",
            "주식병합",
            "최대주주변경",
            "최대주주등소유주식변동",
        ),
    ),
]

# Normalize away interpunct variants so keywords don't break on encoding diffs.
_NORMALIZE_REMOVE = ("ㆍ", "·", "・", "‧", " ", "(", ")", "[", "]")


def _normalize(s: str) -> str:
    out = s
    for ch in _NORMALIZE_REMOVE:
        out = out.replace(ch, "")
    return out


def _strip_prefix(name: str) -> str:
    """[기재정정], [첨부추가] 같은 대괄호 prefix 제거."""
    s = name.strip()
    while s.startswith("["):
        end = s.find("]")
        if end < 0:
            break
        s = s[end + 1 :].strip()
    return s


def classify(d: Disclosure) -> str:
    name_norm = _normalize(_strip_prefix(d.report_nm or ""))
    for signal, keywords in SIGNAL_RULES:
        for kw in keywords:
            if _normalize(kw) in name_norm:
                return signal
    return SIGNAL_NEUTRAL
