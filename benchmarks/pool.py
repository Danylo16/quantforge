"""Measure spawned pool setup, dispatch and returned scores on a fixed grid."""

import json
import pickle
import tempfile
import time
from pathlib import Path

from quantforge.data import generate, load
from quantforge.engine import Config
from quantforge.research import grid, search

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        file = Path(tmp) / "bars.csv"
        generate(file, 10000, 42)
        bars = load(file)
    cs = grid(["sma", "momentum"], [2, 5], [10, 20])
    samples = []
    baseline = search(bars, cs, Config(), 1, 1)
    for workers in [1, 2]:
        for trial in range(4):
            start = time.perf_counter()
            assert search(bars, cs, Config(), 1, workers) == baseline
            elapsed = time.perf_counter() - start
            if trial:
                samples.append({"workers": workers, "seconds": elapsed})
    print(
        json.dumps(
            {
                "n": len(bars),
                "candidates": len(cs),
                "bars_pickle_bytes": len(pickle.dumps(bars)),
                "samples": samples,
            },
            indent=2,
        )
    )
