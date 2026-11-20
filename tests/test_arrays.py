from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from quantforge.arrays import simulate_array
from quantforge.data import load
from quantforge.engine import Config, simulate, strategy


@given(
    st.sampled_from(["sma", "buy-hold", "mean-reversion", "momentum"]),
    st.integers(0, 100),
    st.integers(1, 3),
)
def test_array_ledger(name, size, fast):
    bars = load(Path(__file__).resolve().parents[1] / "examples/golden.csv")
    config = Config(50, 0.3, 0.012, 0.01)
    for i in range(1, 5):
        part = bars[:i]
        assert simulate_array(part, name, size, fast, fast + 1, config) == simulate(
            part, strategy(name, size, fast, fast + 1), config
        )


def test_invalid_arrays():
    bars = load(Path(__file__).resolve().parents[1] / "examples/golden.csv")
    for data, name in [([], "momentum"), (bars[::-1], "buy-hold"), (bars, "bad")]:
        with pytest.raises(ValueError):
            simulate_array(data, name, 1, 1, 2, Config())
