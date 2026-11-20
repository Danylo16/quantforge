from dataclasses import replace

from quantforge.data import generate, load
from quantforge.engine import Config
from quantforge.research import experiment, grid, search


def test_parallel_and_holdout(tmp_path):
    path = tmp_path / "prices.csv"
    generate(path, 40, 123)
    bars = load(path)
    cs = grid(["sma", "momentum"], [1], [2, 5])
    assert search(bars, cs, Config(), 1, 1) == search(bars, cs, Config(), 1, 2)

    def run(data):
        return experiment(data, cs, Config(), 1, 1, 15, 12)

    first = run(bars)
    mutated = bars[:27] + [
        replace(b, open=900, high=900, low=900, close=900) for b in bars[27:]
    ]
    second = run(mutated)
    assert {k: v for k, v in first.items() if k != "test"} == {
        k: v for k, v in second.items() if k != "test"
    }
    assert first["test_range"] == [27, 40]
