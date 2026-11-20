# QuantForge 1.0.0

This release includes two deterministic execution paths, four built-in strategies, cost-aware risk and trade analytics, and chronological research with an untouched final partition. Existing Python calls and CLI backtest arguments remain supported. Backtests additionally write metrics.json. Frequency-dependent values require an explicit periods-per-year argument. The default engine remains event-driven.

| Milestone | Evidence |
|---|---|
| 0.2 Analytics | Hand-calculated returns, risk ratios and partial-sale cycles. 25 local tests at milestone. |
| 0.3 Computing | Four built-in strategy paths compared record by record on fixture prefixes. 27 tests. |
| 0.4 Research | Spawned workers match serial results. Mutating final-test prices leaves fitted parameters and validation results unchanged. 28 tests. |
| 0.5 Time series | 383 monthly S&P 500 returns with two surrogate families and two chronological subsamples. |
| 0.6 Performance | 36 isolated-process engine observations before and after profiling. All million-bar runs reconcile at the endpoint. |
| 0.7 Reliability | Long Decimal cash audit, prefix invariance, zero-equity and overflow cases, end-to-end CLI tests. |
| 1.0 Delivery | Reproducible research, source installation, buildable wheel, CI, versioned reports and examples. |

## Architecture
The data module normalises time and validates bars. The event engine invokes a fresh causal strategy callable after close. The array engine receives one of four named strategies, builds targets and independently accounts for next-open executions. Both emit Result(marks, orders, fills). Analytics consumes that immutable-record history; research evaluates fresh strategy instances on disjoint evaluation windows. The CLI owns I/O, hashes and output staging. See [architecture decisions](decisions.md) and [metric definitions](analytics.md).
