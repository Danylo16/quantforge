from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quantforge.analytics import analyse
from quantforge.data import load
from quantforge.engine import Config, Mark, Result, simulate, strategy

FILE = Path(__file__).resolve().parents[1] / "examples/golden.csv"


def test_two_period_oracle():
    # Two equally weighted half-year observations: +25%, -20%; zero cumulative return.
    start = datetime(2020, 1, 1, tzinfo=UTC)
    marks = [
        Mark(start + timedelta(days=180 * i), e, 0, 0, 0, 0, 0, e, 0)
        for i, e in enumerate([100, 125, 100])
    ]
    m = analyse(Result(marks, [], []), 2)["values"]
    assert m["annual_volatility"] == pytest.approx(0.45)
    assert m["sharpe"] == pytest.approx(0.05 / 0.45)
    assert m["sortino"] == pytest.approx(0.25)
    assert [m[k] for k in ("total_return", "cagr", "calmar", "max_drawdown")] == [
        0,
        0,
        0,
        0.2,
    ]
    assert m["win_rate"] is None


def test_trade_statistics():
    targets = iter([4, 2, 0, 0])
    r = simulate(load(FILE), lambda _: next(targets), Config(100, 1))
    m = analyse(r)["values"]
    assert m["trade_count"] == m["win_rate"] == 1
    assert m["average_trade_return"] == pytest.approx(1 / 41)
    assert m["profit_factor"] is None
    assert m["turnover"] == pytest.approx(84 / 103.5)
    assert m["exposure"] == pytest.approx((48 / 107 + 22 / 106) / 4)


@pytest.mark.parametrize(
    ("name", "targets"), [("momentum", [0, 0, 1, 0]), ("mean-reversion", [0, 0, 0, 1])]
)
def test_causal_windows(name, targets):
    bars = load(FILE)
    for n in range(1, 5):
        model = strategy(name, 1, 1, 2)
        assert [model(b) for b in bars[:n]] == targets[:n]


def test_one_year_rf_and_compounding():
    from datetime import timedelta

    start = datetime(2020, 1, 1, tzinfo=UTC)
    half_year = timedelta(days=365.2425 / 2)
    marks = [
        Mark(start + i * half_year, e, 0, 0, 0, 0, 0, e, 0)
        for i, e in enumerate([100, 110, 99])
    ]
    m = analyse(Result(marks, [], []), 2, 0.0201)["values"]
    assert m["cagr"] == pytest.approx(-0.01)
    assert m["calmar"] == pytest.approx(-0.1)
    assert m["max_drawdown"] == pytest.approx(0.1)
    assert m["sharpe"] == pytest.approx(-0.1)
    assert m["sortino"] == pytest.approx(-0.02 / 0.11)
