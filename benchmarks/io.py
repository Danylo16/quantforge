"""Compare strict loader wall time on equivalent CSV and Parquet workloads."""

import json
import tempfile
import time
from pathlib import Path

import pyarrow.csv as pc
import pyarrow.parquet as pq

from quantforge.data import generate, load

if __name__ == "__main__":
    results = []
    with tempfile.TemporaryDirectory() as directory:
        for n in [10000, 100000, 1000000]:
            csv = Path(directory) / f"{n}.csv"
            parquet = csv.with_suffix(".parquet")
            generate(csv, n, 42)
            pq.write_table(pc.read_csv(csv), parquet)
            for file in [csv, parquet]:
                for trial in range(4):
                    start = time.perf_counter()
                    bars = load(file)
                    elapsed = time.perf_counter() - start
                    assert len(bars) == n
                    del bars
                    if trial:
                        results.append(
                            {
                                "rows": n,
                                "format": file.suffix,
                                "seconds": elapsed,
                                "bytes": file.stat().st_size,
                            }
                        )
            print(n, flush=True)
            (Path(__file__).parent / "io.json").write_text(
                json.dumps(results, indent=2) + "\n"
            )
