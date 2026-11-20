from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quantforge.data import load
from quantforge.engine import Config, simulate, strategy

FILE = Path(__file__).resolve().parents[1] / "examples/golden.csv"


def test_known_inventory():
    targets = iter([4, 2, 0, 0])
    r = simulate(load(FILE), lambda _: next(targets), Config(100, 1))
    assert [m.equity for m in r.marks] == [100, 107, 106, 101]
    assert [m.cash for m in r.marks] == [100, 59, 84, 101]
    assert [m.realised for m in r.marks] == [0, 0, 4.5, 1]
    assert [m.unrealised for m in r.marks] == [0, 7, 1.5, 0]
    assert [f.delta for f in r.fills] == [4, -2, -2]
    assert r.marks[-1].fees == 3


def test_gap_reject_and_retry():
    bars = load(FILE)
    r = simulate(bars, lambda _: 10, Config(100, 1))
    assert [o.status for o in r.orders] == ["insufficient_cash"] * 2 + ["filled"]
    assert r.fills[0].timestamp == bars[-1].timestamp
    assert r.marks[-1].cash == 9


@pytest.mark.parametrize("capital,expected", [(101, 1), (100.9999999, 0)])
def test_boundary(capital, expected):
    r = simulate(load(FILE)[:2], lambda _: 10, Config(capital, 1))
    assert len(r.fills) == expected


@given(st.lists(st.integers(0, 15), min_size=4, max_size=4))
def test_decimal_ledger(targets):
    bars = load(FILE)
    sequence = iter(targets)
    r = simulate(bars, lambda _: next(sequence), Config(100, 0.25, 0.003, 0.01))
    cash = Decimal(100)
    position = 0
    for i, (bar, mark) in enumerate(zip(bars, r.marks, strict=True)):
        delta = (targets[i - 1] if i else 0) - position
        if delta:
            price = Decimal(str(bar.open)) * Decimal("1.01" if delta > 0 else "0.99")
            balance = (
                cash
                - delta * price
                - Decimal(".25")
                - abs(delta) * price * Decimal(".003")
            )
            if balance >= 0:
                cash, position = balance, position + delta
        assert mark.position == position
        assert mark.cash == pytest.approx(float(cash), abs=1e-11, rel=1e-12)
        assert mark.equity == pytest.approx(100 + mark.realised + mark.unrealised)
        assert mark.equity == pytest.approx(float(cash) + position * bar.close)


def test_prefix_and_warmup():
    bars = load(FILE)

    def run(data):
        return simulate(data, strategy("sma", 2, 1, 2), Config())

    full = run(bars)
    assert [m.target for m in full.marks] == [0, 2, 0, 0]
    for n in range(1, len(bars) + 1):
        assert run(bars[:n]).marks == full.marks[:n]
    assert run(bars) == full


@pytest.mark.parametrize("config", [(-1, 0, 0, 0), (1, -1, 0, 0), (1, 0, 0, 1)])
def test_invalid_config(config):
    with pytest.raises(ValueError):
        Config(*config)


def test_invalid_inputs():
    bars = load(FILE)
    for data, decide in [
        ([], lambda _: 1),
        (bars[::-1], lambda _: 0),
        (bars, lambda _: -2),
    ]:
        with pytest.raises(ValueError):
            simulate(data, decide, Config())
    with pytest.raises(ValueError):
        strategy("sma", 1, 3, 2)
