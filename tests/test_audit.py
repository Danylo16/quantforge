import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from quantforge.analytics import analyse
from quantforge.arrays import simulate_array
from quantforge.data import Bar
from quantforge.engine import Config, simulate, strategy


def path(prices):
    start = datetime(2020, 1, 1, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=i), price, price, price, price, 1)
        for i, price in enumerate(prices)
    ]


def test_long_decimal_and_causal_audit():
    prices = [float(64 + (i % 13) / 8) for i in range(8192)]
    bars = path(prices)
    cfg = Config(1000, 0.125, 0.0001, 0.001)
    result = simulate_array(bars, "momentum", 4, 1, 3, cfg)
    assert result == simulate(bars, strategy("momentum", 4, 1, 3), cfg)
    assert result == simulate_array(bars, "momentum", 4, 1, 3, cfg)
    cash = Decimal(1000)
    pos = 0
    for i, mark in enumerate(result.marks):
        target = 4 if i >= 4 and prices[i - 1] > prices[i - 4] else 0
        delta = target - pos
        if delta:
            price = Decimal(str(prices[i])) * (
                Decimal("1.001") if delta > 0 else Decimal(".999")
            )
            fee = Decimal(".125") + abs(delta) * price * Decimal(".0001")
            balance = cash - delta * price - fee
            if balance >= 0:
                cash, pos = balance, target
        assert mark.position == pos
        assert mark.cash == pytest.approx(float(cash), abs=1e-9, rel=1e-12)
        assert mark.equity == pytest.approx(
            1000 + mark.realised + mark.unrealised, abs=1e-9
        )
    for n in [1, 19, 2017]:
        assert (
            simulate_array(bars[:n], "momentum", 4, 1, 3, cfg).marks == result.marks[:n]
        )


def test_bankruptcy_and_risk_inputs():
    bars = path([2.0, 2.0, 1.0, 1.0])
    seq = iter([1, 0, 0, 0])
    r = simulate(bars, lambda _: next(seq), Config(3, 1))
    m = analyse(r, 12)
    assert m["values"]["total_return"] == -1
    assert m["values"]["max_drawdown"] == 1
    assert m["values"]["cagr"] == -1
    assert m["values"]["exposure"] is None
    for periods, rf in [(0, 0), (math.inf, 0), (12, -1)]:
        with pytest.raises(ValueError):
            analyse(r, periods, rf)


def test_extreme_values():
    bars = path([1e308, 1e308])
    with pytest.raises(ValueError, match="overflow"):
        simulate_array(bars, "buy-hold", 2, 1, 2, Config(1e308))
    with pytest.raises(ValueError, match="overflow"):
        simulate(bars, strategy("buy-hold", 2, 1, 2), Config(1e308))
    with pytest.raises(ValueError, match="int64"):
        simulate_array(bars, "buy-hold", 2**64, 1, 2, Config())
