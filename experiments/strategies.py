"""Generate a synthetic, cost-aware comparison and training sensitivity figure."""

import json
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from quantforge.cli import digest
from quantforge.data import generate, load
from quantforge.engine import Config, simulate, strategy
from quantforge.research import experiment, grid

if __name__ == "__main__":
    output = Path(__file__).parent
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "prices.csv"
        generate(file, 600, 42)
        checksum = digest(file)
        bars = load(file)
    cfg = Config(10000, 0.10, 0.0002, 0.0001)
    fig, axes = plt.subplots(3, 1, figsize=(7.5, 7.5), layout="constrained")
    plt.rcParams.update(
        {
            "svg.fonttype": "none",
            "svg.hashsalt": "quantforge",
            "path.simplify_threshold": 0.5,
        }
    )
    for name in ["buy-hold", "momentum", "sma", "mean-reversion"]:
        result = simulate(bars, strategy(name, 40, 5, 20), cfg)
        equity = np.array([m.equity for m in result.marks])
        axes[0].plot(equity, label=name, lw=1)
        axes[1].plot(100 * (equity / np.maximum.accumulate(equity) - 1), lw=1)
    axes[0].set(ylabel="Equity", title="Synthetic minute bars, seed 42")
    axes[0].legend(ncol=2, fontsize=8)
    axes[1].set(ylabel="Drawdown (%)", xlabel="Bar")
    fast = [2, 5, 10]
    slow = [12, 20, 40]
    report = experiment(bars, grid(["sma"], fast, slow), cfg, 40, 1, 300, 150)
    report.update(
        input_sha256=checksum,
        seed=42,
        source="QuantForge minute generator",
        version="1.0.0",
    )
    (output / "strategy-study.json").write_text(json.dumps(report, indent=2) + "\n")
    values = np.array([r["return"] for r in report["final_train_scores"]]).reshape(3, 3)
    heat = axes[2].imshow(values * 100, aspect="auto", cmap="viridis")
    axes[2].set(
        xticks=range(3),
        xticklabels=slow,
        yticks=range(3),
        yticklabels=fast,
        xlabel="Slow window",
        ylabel="Fast window",
        title="SMA training return, bars 0–449",
    )
    fig.colorbar(heat, ax=axes[2], label="Return (%)")
    fig.savefig(output / "strategies.svg", metadata={"Date": None})
