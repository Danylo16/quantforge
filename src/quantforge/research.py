"""Chronological rolling-origin research with one untouched final partition."""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from itertools import product
from multiprocessing import get_context

from .data import Bar
from .engine import Config, simulate, strategy


@dataclass(frozen=True, order=True)
class Candidate:
    strategy: str
    fast: int
    slow: int


def grid(names: list[str], fast: list[int], slow: list[int]) -> list[Candidate]:
    candidates = {
        Candidate(name, f if name == "sma" else 1, s if name != "buy-hold" else 1)
        for name, f, s in product(names, fast, slow)
        if name != "sma" or 0 < f < s
    }
    if not candidates or any(
        c.slow < 1
        or c.strategy not in {"sma", "momentum", "mean-reversion", "buy-hold"}
        for c in candidates
    ):
        raise ValueError("invalid parameter grid")
    return sorted(candidates)


def evaluate(
    bars: list[Bar], candidate: Candidate, config: Config, size: int
) -> dict[str, float]:
    result = simulate(
        bars, strategy(candidate.strategy, size, candidate.fast, candidate.slow), config
    )
    peak = config.capital
    loss = 0.0
    for m in result.marks:
        peak = max(peak, m.equity)
        loss = max(loss, (peak - m.equity) / peak)
    return {
        "return": (result.marks[-1].equity - config.capital) / config.capital,
        "drawdown": loss,
        "fees": result.marks[-1].fees,
    }


def _score(args: tuple[list[Bar], Candidate, Config, int]) -> dict[str, float]:
    return evaluate(*args)


def search(
    bars: list[Bar],
    candidates: list[Candidate],
    config: Config,
    size: int,
    workers: int,
) -> list[dict[str, float]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    jobs = [(bars, c, config, size) for c in candidates]
    if workers == 1:
        return [_score(j) for j in jobs]
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context("spawn")
    ) as pool:
        return list(pool.map(_score, jobs))


def experiment(
    bars: list[Bar],
    candidates: list[Candidate],
    config: Config,
    size: int,
    workers: int,
    train: int,
    validation: int,
    objective: str = "return",
) -> dict[str, object]:
    """Expanding training windows; full validation blocks, then one final test."""
    if train < 2 or validation < 1 or train + validation >= len(bars) or not candidates:
        raise ValueError("need train, validation and nonempty final test")
    if objective not in {"return", "drawdown"}:
        raise ValueError("unknown objective")
    cutoff = train + validation
    width = max(1, validation // 3)
    folds = []

    def select(end: int) -> tuple[Candidate, list[dict[str, float]]]:
        scores = search(bars[:end], candidates, config, size, workers)
        index = max(
            range(len(scores)),
            key=lambda i: scores[i][objective] * (1 if objective == "return" else -1),
        )
        return candidates[index], scores

    for end in range(train, cutoff, width):
        winner, scores = select(end)
        stop = min(end + width, cutoff)
        folds.append(
            {
                "train": [0, end],
                "validation": [end, stop],
                "candidate": asdict(winner),
                "sensitivity": scores,
                "out_of_sample": evaluate(bars[end:stop], winner, config, size),
            }
        )
    final, scores = select(cutoff)
    return {
        "candidates": [asdict(c) for c in candidates],
        "objective": objective,
        "workers": workers,
        "config": asdict(config),
        "units": size,
        "folds": folds,
        "final_candidate": asdict(final),
        "final_train_scores": scores,
        "test_range": [cutoff, len(bars)],
        "test": evaluate(bars[cutoff:], final, config, size),
    }
