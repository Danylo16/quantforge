"""Run each full-audit simulation in a fresh process. Linux RSS units are KiB."""

import argparse
import json
import platform
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from quantforge.arrays import simulate_array
from quantforge.data import Bar
from quantforge.engine import Config, simulate, strategy


def measure(n: int, engine: str) -> dict[str, object]:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    bars = []
    for i in range(n):
        price = float(100 + (i % 40))
        bars.append(Bar(start + timedelta(minutes=i), price, price, price, price, 100))

    def run(data: list[Bar]):
        if engine == "array":
            return simulate_array(data, "momentum", 1, 2, 10, Config())
        return simulate(data, strategy("momentum", 1, 2, 10), Config())

    run(bars[:1000])
    clock = time.perf_counter()
    result = run(bars)
    elapsed = time.perf_counter() - clock
    return {
        "n": n,
        "engine": engine,
        "seconds": elapsed,
        "rows_s": n / elapsed,
        "peak_process_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "final": result.marks[-1].equity,
        "fills": len(result.fills),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(measure(int(args.worker[0]), args.worker[1])))
    else:
        import numpy

        output = {
            "python": sys.version,
            "platform": platform.platform(),
            "cpu": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")
                ),
                "unknown",
            ),
            "numpy": numpy.__version__,
            "workers": 1,
            "warmup": 1000,
            "samples": [],
        }
        for n in [10000, 100000, 1000000]:
            for repeat in range(3):
                for engine in ["event", "array"]:
                    raw = subprocess.check_output(
                        [sys.executable, __file__, "--worker", str(n), engine]
                    )
                    output["samples"].append(dict(repeat=repeat, **json.loads(raw)))
                    args.output.write_text(json.dumps(output, indent=2) + "\n")
