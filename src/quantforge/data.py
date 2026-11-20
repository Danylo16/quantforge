"""Strict OHLCV ingestion. Timestamps denote session labels."""

import csv
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

FIELDS = ("timestamp", "open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must have a timezone")
        prices = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(x) and x > 0 for x in prices):
            raise ValueError("prices must be finite and positive")
        if self.low > min(self.open, self.close) or self.high < max(
            self.open, self.close
        ):
            raise ValueError("invalid price range")
        if not math.isfinite(self.volume) or self.volume < 0:
            raise ValueError("invalid volume")


def timestamp(value: str, zone: str | None) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        if zone is None:
            raise ValueError("naive timestamp requires an explicit timezone")
        local = dt.replace(tzinfo=ZoneInfo(zone))
        if local.utcoffset() != local.replace(fold=1).utcoffset():
            raise ValueError("ambiguous or nonexistent local time requires an offset")
        dt = local
    return dt.astimezone(UTC)


def load(
    path: Path, zone: str | None = None, calendar: Path | None = None
) -> list[Bar]:
    rows: list[list[object]]
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            names = next(reader, [])
            rows = [list(row) for row in reader]
    elif path.suffix.lower() == ".parquet":
        import pyarrow.parquet as pq

        table = pq.read_table(path)
        names = table.column_names
        rows = [list(row) for row in zip(*(col.to_pylist() for col in table.columns))]
    else:
        raise ValueError("expected CSV or Parquet")
    if sorted(names) != sorted(FIELDS):
        raise ValueError(f"expected exactly {FIELDS}")
    bars: list[Bar] = []
    for i, row in enumerate(rows, 2):
        try:
            record = dict(zip(names, row, strict=True))
            bar = Bar(
                timestamp(str(record["timestamp"]), zone),
                *(float(str(record[key])) for key in FIELDS[1:]),
            )
            if bars and bars[-1].timestamp >= bar.timestamp:
                raise ValueError("duplicate or unordered timestamp")
        except ValueError as error:
            raise ValueError(f"row {i}: {error}") from error
        bars.append(bar)
    if not bars:
        raise ValueError("empty dataset")
    if calendar is not None:
        expected = [timestamp(line, zone) for line in calendar.read_text().splitlines()]
        if expected != [bar.timestamp for bar in bars]:
            raise ValueError("bars differ from the supplied session schedule")
    return bars


def generate(path: Path, count: int, seed: int) -> None:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    price = 100.0
    start = datetime(2020, 1, 1, tzinfo=UTC)
    with path.open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for i in range(count):
            close = price * math.exp(rng.gauss(0, 0.001))
            writer.writerow(
                (
                    start + timedelta(minutes=i),
                    price,
                    max(price, close),
                    min(price, close),
                    close,
                    rng.randrange(100, 10000),
                )
            )
            price = close
