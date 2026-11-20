"""Monthly S&P 500 dependence study; external estimator pinned by blob checksum."""

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fractal_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    estimator = args.fractal_root / "src/hurts.py"
    if (
        hashlib.sha256(estimator.read_bytes()).hexdigest()
        != "e0870b2bfe08ae2c4afaf6f298c9fae29665892190e724e2027e40bffa4d230c"
    ):
        raise ValueError("unexpected R/S estimator version")
    spec = importlib.util.spec_from_file_location("man_rs", estimator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = Path(matplotlib.get_data_path()) / "sample_data/Stocks.csv"
    with source.open() as f:
        rows = [
            r
            for r in csv.DictReader(line for line in f if not line.startswith("#"))
            if r["^GSPC"] and r["Date"] < "2022-01-01"
        ]
    months = np.array([r["Date"][:7] for r in rows], dtype="datetime64[M]")
    if not np.all(np.diff(months).astype(int) == 1):
        raise ValueError("expected consecutive months")
    ret = np.diff(np.log([float(r["^GSPC"]) for r in rows]))
    months = months[1:]
    rng = np.random.default_rng(42)

    def hurst(x):
        return module.hurst_rs(x, min_win=8, max_win=32)[0]

    def ac(x):
        return float(np.corrcoef(x[1:], x[:-1])[0, 1])

    def summary(x):
        blocks = [x[i : i + 6] for i in range(0, len(x), 6)]
        shuffled = [hurst(rng.permutation(x)) for _ in range(99)]
        block = [
            hurst(np.concatenate([blocks[i] for i in rng.permutation(len(blocks))]))
            for _ in range(99)
        ]
        return {
            "n": len(x),
            "hurst": hurst(x),
            "annual_volatility": float(np.std(x, ddof=1) * np.sqrt(12)),
            "lag1": ac(x),
            "shuffled_H_q05_median_q95": np.quantile(
                shuffled, [0.05, 0.5, 0.95]
            ).tolist(),
            "six_month_block_H_q05_median_q95": np.quantile(
                block, [0.05, 0.5, 0.95]
            ).tolist(),
        }

    data = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "matplotlib": matplotlib.__version__,
        "numpy": np.__version__,
        "seed": 42,
        "start": str(months[0]),
        "end": str(months[-1]),
        "full": summary(ret),
        "pre_2006": summary(ret[months < np.datetime64("2006-01")]),
        "since_2006": summary(ret[months >= np.datetime64("2006-01")]),
    }
    windows = np.lib.stride_tricks.sliding_window_view(ret, 24)
    rolling = np.array([ac(x) for x in windows])
    # At month t, classify using only the preceding 24 months.
    vol = np.std(windows[:-1], axis=1, ddof=1) * np.sqrt(12)
    for label, mask in [("high", vol >= 0.15), ("low", vol < 0.15)]:
        sample = ret[24:][mask]
        data[label + "_prior_vol"] = {
            "months": len(sample),
            "mean_next_log_return": float(sample.mean()),
        }
    args.output.mkdir(exist_ok=True)
    (args.output / "market.json").write_text(json.dumps(data, indent=2) + "\n")
    with (args.output / "monthly-statistics.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["month", "rolling24_lag1", "rolling24_ann_vol"])
        writer.writerows(
            zip(
                months[23:].astype(str),
                rolling,
                np.std(windows, axis=1, ddof=1) * np.sqrt(12),
                strict=True,
            )
        )
    matplotlib.rcParams["svg.hashsalt"] = "quantforge"
    matplotlib.rcParams["svg.fonttype"] = "none"
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(8, 4.5), layout="constrained")
    axes[0].plot(months[23:], rolling, lw=1)
    axes[0].axhline(0, color="grey", lw=0.6)
    axes[0].set_ylabel("Lag-one correlation")
    axes[1].plot(months[23:], np.std(windows, axis=1, ddof=1) * np.sqrt(12) * 100, lw=1)
    axes[1].set_ylabel("Annual volatility (%)")
    axes[0].set_title("S&P 500 monthly log returns • trailing 24 months")
    fig.savefig(args.output / "dependence.svg", metadata={"Date": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
