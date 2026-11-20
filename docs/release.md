# QuantForge 1.0.0

This release includes two deterministic execution paths, four built-in strategies, cost-aware risk and trade analytics, and chronological research with an untouched final partition. Existing Python calls and CLI backtest arguments remain supported. Backtests additionally write metrics.json. Frequency-dependent values require an explicit periods-per-year argument. The default engine remains event-driven.

| Milestone | Evidence | Interview prompt |
|---|---|---|
| 0.2 Analytics | Hand-calculated returns, risk ratios and partial-sale cycles. 25 local tests at milestone. | Why can a round trip to initial equity have positive arithmetic mean return? |
| 0.3 Computing | Four built-in strategy paths compared record by record on fixture prefixes. 27 tests. | Which order decisions depend on the fill ledger? |
| 0.4 Research | Spawned workers match serial results. Mutating final-test prices leaves fitted parameters and validation results unchanged. 28 tests. | When does a validation bar become eligible for training? |
| 0.5 Time series | 383 monthly S&P 500 returns with two surrogate families and two chronological subsamples. | Why does H above 0.5 also occur on shuffled data? |
| 0.6 Performance | 36 isolated-process engine observations before and after profiling. All million-bar runs reconcile at the endpoint. | Why does the array path retain O(n) memory even with sparse fills? |
| 0.7 Reliability | Long Decimal cash audit, prefix invariance, zero-equity and overflow cases, end-to-end CLI tests. | Why should cash acceptance use a different rule from approximate equality in a test? |
| 1.0 Delivery | Reproducible research, source installation, buildable wheel, CI, versioned reports and examples. | What would have to change for dividend-paying multi-asset portfolios? |

## Architecture
The data module normalises time and validates bars. The event engine invokes a fresh causal strategy callable after close. The array engine receives one of four named strategies, builds targets and independently accounts for next-open executions. Both emit Result(marks, orders, fills). Analytics consumes that immutable-record history; research evaluates fresh strategy instances on disjoint evaluation windows. The CLI owns I/O, hashes and output staging. See [architecture decisions](decisions.md) and [metric definitions](analytics.md).

## Technical article outline
1. Reconstruct a gapped next-open fill by hand.
2. Compare the independent decimal and binary64 cash ledgers.
3. Show why an affordability rejection breaks a naive shifted-position calculation.
4. Measure where full-audit vectorisation pays off, including process memory.
5. Repeat selection across expanding windows and contrast the held-out result with the training heatmap.
6. Interpret the observed Hurst estimate alongside its finite-sample surrogate distribution.

## CV description
Built a Python/NumPy backtesting library with independent event and array execution paths, fee-aware portfolio accounting, and chronological walk-forward evaluation. Audited cash against a Decimal reference and benchmarked full trade histories on up to one million bars.
