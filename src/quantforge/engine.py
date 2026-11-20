"""Causal close-to-next-open simulation with average-cost inventory."""

import math
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from .data import Bar

Strategy = Callable[[Bar], int]


def units(value: int) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("target must be a nonnegative integer")
    return value


def strategy(name: str, size: int, fast: int, slow: int) -> Strategy:
    units(size)
    if name == "buy-hold":
        return lambda bar: size
    if name in {"momentum", "mean-reversion"}:
        if slow < 1:
            raise ValueError("lookback must be positive")
        window: deque[float] = deque(maxlen=slow)

        def signal(bar: Bar) -> int:
            target = 0
            if len(window) == slow:
                if name == "momentum":
                    enter = bar.close > window[0]
                else:
                    enter = bar.close < math.fsum(window) / slow
                target = size if enter else 0
            window.append(bar.close)
            return target

        return signal
    if name != "sma" or not 0 < fast < slow:
        raise ValueError("SMA requires 0 < fast < slow")
    short: deque[float] = deque()
    long: deque[float] = deque()
    short_sum = long_sum = 0.0

    def update(bar: Bar) -> int:
        nonlocal short_sum, long_sum
        short.append(bar.close)
        long.append(bar.close)
        short_sum += bar.close
        long_sum += bar.close
        if len(short) > fast:
            short_sum -= short.popleft()
        if len(long) > slow:
            long_sum -= long.popleft()
        return size if len(long) == slow and short_sum / fast > long_sum / slow else 0

    return update


@dataclass(frozen=True)
class Config:
    capital: float = 10000
    fixed: float = 0
    rate: float = 0
    slip: float = 0

    def __post_init__(self) -> None:
        if not all(math.isfinite(x) and x >= 0 for x in vars(self).values()):
            raise ValueError("capital and costs must be finite and nonnegative")
        if self.capital == 0 or self.slip >= 1:
            raise ValueError("capital must be positive and slip below one")


class Order(NamedTuple):
    signal_time: datetime
    timestamp: datetime
    delta: int
    status: str


class Fill(NamedTuple):
    timestamp: datetime
    delta: int
    price: float
    fee: float


class Mark(NamedTuple):
    timestamp: datetime
    cash: float
    position: int
    basis: float
    realised: float
    unrealised: float
    fees: float
    equity: float
    target: int


class Result(NamedTuple):
    marks: list[Mark]
    orders: list[Order]
    fills: list[Fill]


def simulate(bars: Iterable[Bar], decide: Strategy, config: Config) -> Result:
    result = Result([], [], [])
    cash = config.capital
    target = position = 0
    cost = realised = fees = 0.0
    previous: datetime | None = None
    for bar in bars:
        if previous is not None and previous >= bar.timestamp:
            raise ValueError("unordered bars")
        delta = target - position
        if delta and previous is not None:
            price = bar.open * (1 + math.copysign(config.slip, delta))
            fee = config.fixed + abs(delta) * price * config.rate
            balance = cash - delta * price - fee
            if not math.isfinite(balance):
                raise ValueError("cash overflow")
            accepted = balance >= 0
            result.orders.append(
                Order(
                    previous,
                    bar.timestamp,
                    delta,
                    "filled" if accepted else "insufficient_cash",
                )
            )
            if accepted:
                if delta > 0:
                    cost = (position * cost + delta * price + fee) / target
                else:
                    realised += -delta * (price - cost) - fee
                    if target == 0:
                        cost = 0.0
                cash, position, fees = balance, target, fees + fee
                result.fills.append(Fill(bar.timestamp, delta, price, fee))
        target = units(decide(bar))
        unrealised = position * (bar.close - cost)
        equity = cash + position * bar.close
        if not all(
            math.isfinite(x) for x in (equity, unrealised, realised, fees, cost)
        ):
            raise ValueError("accounting overflow")
        result.marks.append(
            Mark(
                bar.timestamp,
                cash,
                position,
                cost,
                realised,
                unrealised,
                fees,
                equity,
                target,
            )
        )
        previous = bar.timestamp
    if previous is None:
        raise ValueError("empty dataset")
    return result
