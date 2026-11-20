import json
import sys

from quantforge.cli import main


def test_reproduce_both_entrypoints(tmp_path, monkeypatch):
    def run(*args):
        monkeypatch.setattr(sys, "argv", ["quantforge", *(str(x) for x in args)])
        main()

    prices = tmp_path / "bars.csv"
    run("generate", prices, "--count", 100)
    run("research", prices, tmp_path / "study.json", "--train", 40, "--validation", 30)
    study = json.loads((tmp_path / "study.json").read_text())
    assert study["test_range"] == [70, 100]
    for engine in ["event", "array"]:
        run(
            "backtest",
            prices,
            tmp_path / engine,
            "--engine",
            engine,
            "--strategy",
            "momentum",
        )
    for name in ["equity.csv", "orders.csv", "fills.csv", "metrics.json"]:
        assert (tmp_path / "event" / name).read_bytes() == (
            tmp_path / "array" / name
        ).read_bytes()
