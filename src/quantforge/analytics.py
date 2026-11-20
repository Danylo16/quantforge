"""Close-to-close performance and flat-to-flat trade statistics."""

import itertools
import math
from statistics import fmean, stdev
from typing import TypedDict

from .engine import Result


class Metrics(TypedDict):
    values: dict[str, float | int | None]
    undefined: dict[str, str]


def analyse(
    result: Result, periods: float | None = None, risk_free: float = 0
) -> Metrics:
    """Annual frequency is an explicit assertion of equally weighted return periods."""
    if periods is not None and (not math.isfinite(periods) or periods < 1):
        raise ValueError("periods per year must be finite and at least one")
    if not math.isfinite(risk_free) or risk_free <= -1:
        raise ValueError("annual effective risk-free rate must exceed -1")
    marks = result.marks
    if not marks:
        raise ValueError("empty equity series")
    equity = [m.equity for m in marks]
    if equity[0] <= 0 or any(e < 0 or not math.isfinite(e) for e in equity):
        raise ValueError(
            "expected positive opening equity and finite nonnegative marks"
        )
    values: dict[str, float | int | None] = {}
    reasons: dict[str, str] = {}

    def record(key: str, value: float | None, reason: str) -> None:
        if value is not None and not math.isfinite(value):
            value, reason = None, "result exceeds float range"
        values[key] = value
        if value is None:
            reasons[key] = reason

    peak = equity[0]
    loss = 0.0
    for e in equity:
        peak = max(peak, e)
        loss = max(loss, (peak - e) / peak)
    values["max_drawdown"] = loss
    total = (equity[-1] - equity[0]) / equity[0]
    record("total_return", total, "result exceeds float range")
    years = (marks[-1].timestamp - marks[0].timestamp).total_seconds() / (
        86400 * 365.2425
    )
    try:
        growth = (
            (
                -1.0
                if equity[-1] == 0
                else math.expm1((math.log(equity[-1]) - math.log(equity[0])) / years)
            )
            if years
            else None
        )
    except OverflowError:
        growth = None
    record("cagr", growth, "zero elapsed time or annual growth exceeds float range")
    record(
        "calmar",
        growth / loss if growth is not None and loss else None,
        "requires CAGR and positive drawdown",
    )
    returns = (
        [(b - a) / a for a, b in itertools.pairwise(equity)]
        if 0 not in equity[:-1]
        else []
    )
    if any(not math.isfinite(r) for r in returns):
        returns = []
    scale = math.sqrt(periods) if periods else None
    vol = stdev(returns) if len(returns) >= 2 else None
    record(
        "annual_volatility",
        vol * scale if vol is not None and scale else None,
        "requires frequency and two returns",
    )
    excess = (
        [r - math.expm1(math.log1p(risk_free) / periods) for r in returns]
        if periods
        else []
    )
    mean = math.fsum(x / len(excess) for x in excess) if excess else 0.0
    downside = (
        math.hypot(*(min(0.0, x) for x in excess)) / math.sqrt(len(excess))
        if excess
        else 0.0
    )
    record(
        "sharpe",
        mean * scale / vol if vol and scale else None,
        "requires frequency and nonzero sample volatility",
    )
    record(
        "sortino",
        mean * scale / downside if downside and scale else None,
        "requires frequency and downside deviation",
    )
    record(
        "exposure",
        fmean((m.equity - m.cash) / m.equity for m in marks) if all(equity) else None,
        "zero equity at a close",
    )
    values["turnover"] = math.fsum(
        abs(f.delta) * f.price for f in result.fills
    ) / fmean(equity)
    pos = 0
    invested = proceeds = 0.0
    pnl: list[float] = []
    trade_returns: list[float] = []
    for fill in result.fills:
        if fill.delta > 0:
            invested += fill.delta * fill.price + fill.fee
        else:
            proceeds += -fill.delta * fill.price - fill.fee
        pos += fill.delta
        if pos == 0:
            pnl.append(proceeds - invested)
            trade_returns.append(pnl[-1] / invested)
            invested = proceeds = 0.0
    losses = -math.fsum(min(0.0, p) for p in pnl)
    values["trade_count"] = len(pnl)
    record("win_rate", fmean(p > 0 for p in pnl) if pnl else None, "no closed trades")
    record(
        "average_trade_return",
        fmean(trade_returns) if pnl else None,
        "no closed trades",
    )
    record(
        "profit_factor",
        math.fsum(max(0.0, p) for p in pnl) / losses if losses else None,
        "no gross losses",
    )
    return {"values": values, "undefined": reasons}
