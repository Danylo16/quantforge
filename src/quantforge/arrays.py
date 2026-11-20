"""Array signals and independent, sequential fill accounting for built-in strategies."""

import math
from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

from .data import Bar
from .engine import Config, Fill, Mark, Order, Result, units


def targets(
    close: NDArray[np.float64], name: str, size: int, fast: int, slow: int
) -> NDArray[np.int64]:
    units(size)
    if size > np.iinfo(np.int64).max:
        raise ValueError("array target exceeds int64")
    out = np.zeros(len(close), dtype=np.int64)
    if name == "buy-hold":
        out.fill(size)
    elif name == "momentum" and slow > 0:
        out[slow:] = (close[slow:] > close[:-slow]) * size
    elif name == "mean-reversion" and slow > 0:
        if len(close) > slow:
            windows = np.lib.stride_tricks.sliding_window_view(close[:-1], slow)
            # fsum matches the specified threshold, including near ties.
            means = np.fromiter(
                (math.fsum(row) / slow for row in windows),
                dtype=float,
                count=len(windows),
            )
            out[slow:] = (close[slow:] < means) * size
    elif name == "sma" and 0 < fast < slow:
        # Keep event-engine addition/subtraction order at exact crossing boundaries.
        short_sum = long_sum = 0.0
        for i, x in enumerate(close):
            short_sum += float(x)
            long_sum += float(x)
            if i >= fast:
                short_sum -= float(close[i - fast])
            if i >= slow:
                long_sum -= float(close[i - slow])
            if i + 1 >= slow and short_sum / fast > long_sum / slow:
                out[i] = size
    else:
        raise ValueError("invalid strategy or window")
    return out


def simulate_array(
    bars: Sequence[Bar], name: str, size: int, fast: int, slow: int, config: Config
) -> Result:
    if not bars:
        raise ValueError("empty dataset")
    close = np.fromiter((b.close for b in bars), dtype=float, count=len(bars))
    target = targets(close, name, size, fast, slow)
    del close
    result = Result([], [], [])
    cash = config.capital
    position = 0
    basis = realised = fees = 0.0
    for i, bar in enumerate(bars):
        desired = int(target[i - 1]) if i else 0
        if i and bars[i - 1].timestamp >= bar.timestamp:
            raise ValueError("unordered bars")
        change = desired - position
        if change:
            price = bar.open * (1 + config.slip if change > 0 else 1 - config.slip)
            notional = change * price
            fee = config.fixed + abs(notional) * config.rate
            remaining = cash - notional - fee
            if not math.isfinite(remaining):
                raise ValueError("cash overflow")
            filled = remaining >= 0
            result.orders.append(
                Order(
                    bars[i - 1].timestamp,
                    bar.timestamp,
                    change,
                    "filled" if filled else "insufficient_cash",
                )
            )
            if filled:
                if change > 0:
                    basis = (basis * position + notional + fee) / desired
                else:
                    realised += -change * (price - basis) - fee
                    if desired == 0:
                        basis = 0.0
                cash, position = remaining, desired
                fees += fee
                result.fills.append(Fill(bar.timestamp, change, price, fee))
        equity = cash + position * bar.close
        unrealised = position * (bar.close - basis)
        if not (
            math.isfinite(equity)
            and math.isfinite(unrealised)
            and math.isfinite(realised)
            and math.isfinite(fees)
            and math.isfinite(basis)
        ):
            raise ValueError("accounting overflow")
        result.marks.append(
            Mark(
                bar.timestamp,
                cash,
                position,
                basis,
                realised,
                unrealised,
                fees,
                equity,
                int(target[i]),
            )
        )
    return result
