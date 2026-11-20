# QuantForge
[![CI on Linux and Windows](https://github.com/Danylo16/quantforge/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/Danylo16/quantforge/actions/workflows/check.yml)

QuantForge is a Python 3.12 backtesting engine for long-only strategies on a single asset. A strategy reads a completed price bar and sets a target position. The engine can fill the order at the next open, checks available cash after slippage and fees, and records the balance at each close.

## Reproduce the four-session example

From the repository root, run these commands in a Python 3.12 environment:

```shell
python -m pip install -e ".[dev]"
quantforge backtest examples/golden.csv runs/demo --strategy buy-hold --units 4 --capital 100 --fixed 1
```

The four-session fixture opens at 10 after the first close at 8. A buy-and-hold target of four units uses 40 of the initial 100 plus a fee of 1. The final close is 9, leaving 59 in cash and 36 in inventory.

| Close | Position | Cash | Equity |
|---:|---:|---:|---:|
| 8 | 0 | 100 | 100 |
| 12 | 4 | 59 | 107 |
| 11 | 4 | 59 | 103 |
| 9 | 4 | 59 | 95 |

The [accounting tests](tests/test_core.py) also sell the position in two steps and compare generated target sequences against a separate decimal ledger. The [design decisions](docs/decisions.md) cover execution timing, cost basis and numerical precision.

The run writes `orders.csv`, `fills.csv`, `equity.csv` and `manifest.json` to a new output directory. To try a moving-average crossover on reproducible synthetic data:

```shell
quantforge generate synthetic.csv --count 10000 --seed 42
quantforge backtest synthetic.csv runs/sma --strategy sma --fast 10 --slow 40
```

## Input
CSV and Parquet require timestamp, open, high, low, close and volume. Column order is free. Prices are finite and strictly positive. Bars must be unique, chronological and internally consistent. Supply --timezone for naive timestamps. Use offsets at ambiguous DST transitions. --calendar expects one ISO session label per line for the complete input range. Without it, completeness is unchecked. The generator emits continuous UTC minute bars with volume and no intrabar excursions beyond open and close. Generated paths serve as workloads, not calibrated market models.

## Python API
Call load(path, zone, calendar), construct a fresh strategy(name, size, fast, slow) per run, then call simulate(bars, strategy, Config(...)). A custom callable accepts only the current immutable Bar and returns its nonnegative integer target. It may retain past observations. User code is trusted. The API cannot prevent external data access.

## Verification
    python -m pytest -q --cov=quantforge
    python -m mypy src
    python -m ruff check .

CI runs these checks on pushes and pull requests. Python 3.12 is the tested interpreter. PyArrow provides Parquet decoding. CSV and the accounting loop use the standard library. requirements-tested.txt records versions used for the local checks.

## Limits and next milestones
No exchange calendar is bundled. Supply a point-in-time schedule. Splits, dividends, interest, queue position, liquidity limits and intrabar fills are outside the model. Use one coherent OHLC adjustment basis and document it at source. A current constituent universe can introduce survivorship bias. Only the synthetic fixture ships here.

Version 0.2 implements risk metrics, closed-trade statistics, momentum and mean reversion. See [formulas and conventions](docs/analytics.md). M4 adds an independent array engine. M5 covers chronological research and parallel optimisation. M6 measures million-bar performance and audits numerical boundaries. M7 packages measured research results. See docs/decisions.md.

## Array execution

Use `--engine array` with the four built-in strategies. NumPy computes momentum masks and slippage-adjusted candidate prices. The fill ledger runs independently in chronological order because previous rejections affect later quantities. Both engines return identical audit record types. SMA preserves rolling addition order and mean reversion uses compensated window sums to keep threshold decisions consistent. Array storage adds O(n) working memory to the O(n) audit history. Custom callable strategies use the event engine.

## Chronological research

`quantforge research synthetic.csv study.json --train 6000 --validation 2000 --workers 2 --objective return` expands the training prefix through consecutive validation blocks. Each block starts flat with fresh indicators. The final candidate is fitted on the train-plus-validation prefix, then evaluated once on the remaining bars. Objectives maximize total return or minimize drawdown. Equal scores take the first sorted candidate. The manifest records half-open row ranges, the input hash, costs and every candidate score in grid order. Small blocks can end before warm-up completes.
