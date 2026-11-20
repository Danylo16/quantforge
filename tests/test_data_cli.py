import csv
import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from quantforge.data import FIELDS, generate, load, timestamp

FILE = Path(__file__).resolve().parents[1] / "examples/golden.csv"


def test_formats(tmp_path):
    with FILE.open() as f:
        rows = list(csv.DictReader(f))
    file = tmp_path / "bars.parquet"
    pq.write_table(pa.Table.from_pylist(rows), file)
    schedule = tmp_path / "sessions.txt"
    schedule.write_text("\n".join(row["timestamp"] for row in rows))
    assert load(file, calendar=schedule) == load(FILE)
    schedule.write_text(rows[0]["timestamp"])
    with pytest.raises(ValueError, match="schedule"):
        load(file, calendar=schedule)


@pytest.mark.parametrize(
    "row",
    [
        "",
        "2020-01-01,1,1,1,1,1",
        "2020-01-01T00:00Z,0,2,1,2,2",
        "2020-01-01T00:00Z,1,2,1,3,2",
        "2020-01-01T00:00Z,2,2,1,2,-1",
        "2020-01-01T00:00Z,nan,2,1,2,2",
        "2020-01-01T00:00Z,1,2",
        "2020-01-01T00:00Z,1,2,1,2,2\n2020-01-01T00:00Z,1,2,1,2,2",
    ],
)
def test_invalid_data(tmp_path, row):
    file = tmp_path / "bad.csv"
    file.write_text(",".join(FIELDS) + "\n" + row)
    with pytest.raises(ValueError):
        load(file)


def test_dst():
    assert timestamp("2026-01-05", "Europe/Vienna").hour == 23
    with pytest.raises(ValueError):
        timestamp("2026-10-25T02:30", "Europe/Vienna")


def test_smoke(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    generate(a, 50, 42)
    generate(b, 50, 42)
    assert a.read_bytes() == b.read_bytes()
    out = tmp_path / "out"
    cmd = [
        sys.executable,
        "-m",
        "quantforge.cli",
        "backtest",
        str(FILE),
        str(out),
        "--strategy",
        "buy-hold",
        "--units",
        "4",
        "--capital",
        "100",
        "--fixed",
        "1",
    ]
    subprocess.run(cmd, check=True)
    with (out / "equity.csv").open() as f:
        assert float(list(csv.DictReader(f))[-1]["equity"]) == 95
    assert (
        json.loads((out / "manifest.json").read_text())["completeness"] == "unchecked"
    )
    assert subprocess.run(cmd, check=False).returncode != 0
