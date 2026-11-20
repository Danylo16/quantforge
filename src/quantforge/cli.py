import argparse
import csv
import hashlib
import json
import tempfile
from collections.abc import Iterable
from pathlib import Path

from .analytics import analyse
from .arrays import simulate_array
from .data import generate, load
from .engine import Config, Fill, Mark, Order, simulate, strategy
from .research import experiment, grid


def digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def save(
    path: Path, fields: tuple[str, ...], rows: Iterable[tuple[object, ...]]
) -> None:
    with path.open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="cmd", required=True)
    gen = commands.add_parser("generate")
    gen.add_argument("output", type=Path)
    gen.add_argument("--count", type=int, default=1000)
    gen.add_argument("--seed", type=int, default=42)
    run = commands.add_parser("backtest")
    run.add_argument("input", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument(
        "--strategy",
        choices=["buy-hold", "sma", "momentum", "mean-reversion"],
        default="sma",
    )
    run.add_argument("--engine", choices=["event", "array"], default="event")
    run.add_argument("--units", type=int, default=1)
    run.add_argument("--fast", type=int, default=5)
    run.add_argument("--slow", type=int, default=20)
    run.add_argument("--periods-per-year", type=float)
    run.add_argument("--risk-free", type=float, default=0.0)
    run.add_argument("--timezone")
    run.add_argument("--calendar", type=Path)
    for name, default in (("capital", 10000), ("fixed", 0), ("rate", 0), ("slip", 0)):
        run.add_argument("--" + name, type=float, default=default)
    research = commands.add_parser("research")
    research.add_argument("input", type=Path)
    research.add_argument("output", type=Path)
    research.add_argument("--train", type=int, required=True)
    research.add_argument("--validation", type=int, required=True)
    research.add_argument("--workers", type=int, default=1)
    research.add_argument("--slow", type=int, nargs="+", default=[10, 20, 40])
    research.add_argument("--fast", type=int, nargs="+", default=[2, 5])
    research.add_argument(
        "--strategies", nargs="+", default=["sma", "momentum", "mean-reversion"]
    )
    research.add_argument(
        "--objective", choices=["return", "drawdown"], default="return"
    )
    research.add_argument("--units", type=int, default=1)
    for name, default in (("capital", 10000), ("fixed", 0), ("rate", 0), ("slip", 0)):
        research.add_argument("--" + name, type=float, default=default)
    args = parser.parse_args()
    if args.cmd == "research":
        universe = grid(args.strategies, args.fast, args.slow)
        report = experiment(
            load(args.input),
            universe,
            Config(args.capital, args.fixed, args.rate, args.slip),
            args.units,
            args.workers,
            args.train,
            args.validation,
            args.objective,
        )
        report.update(input_sha256=digest(args.input), version="0.4.0")
        with args.output.open("x") as file:
            json.dump(report, file, indent=2, allow_nan=False)
        return
    if args.cmd == "generate":
        generate(args.output, args.count, args.seed)
        return
    if args.output.exists():
        parser.error("output already exists")
    bars = load(args.input, args.timezone, args.calendar)
    config = Config(args.capital, args.fixed, args.rate, args.slip)
    if args.engine == "array":
        result = simulate_array(
            bars, args.strategy, args.units, args.fast, args.slow, config
        )
    else:
        result = simulate(
            bars, strategy(args.strategy, args.units, args.fast, args.slow), config
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as temporary:
        folder = Path(temporary) / "result"
        folder.mkdir()
        save(folder / "equity.csv", Mark._fields, result.marks)
        save(folder / "orders.csv", Order._fields, result.orders)
        save(folder / "fills.csv", Fill._fields, result.fills)
        metrics = analyse(result, args.periods_per_year, args.risk_free)
        (folder / "metrics.json").write_text(
            json.dumps(metrics, indent=2, allow_nan=False)
        )
        metadata = dict(
            vars(args),
            version="0.4.0",
            input_sha256=digest(args.input),
            calendar_sha256=digest(args.calendar) if args.calendar else None,
            completeness="checked" if args.calendar else "unchecked",
        )
        (folder / "manifest.json").write_text(
            json.dumps(metadata, default=str, indent=2)
        )
        folder.rename(args.output)
    print(
        f"{len(bars)} bars, {len(result.fills)} fills, final equity {result.marks[-1].equity:.9g}"
    )


if __name__ == "__main__":
    main()
