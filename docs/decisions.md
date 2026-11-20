# Accepted design decisions
|Decision|Context and choice|Alternative and cost|Validation|
|---|---|---|---|
|001 Architecture|One Python package and one asset per run; CLI delegates to the public API.|A multi-asset broker needs an ordering and shared cash policy.|CLI smoke and API golden test.|
|002 Execution|Observe close, execute previous target at next open, reject entire unfunded order.|Same-close execution would use unavailable prices; partial fills need another model.|Gap, last bar and rejected-order tests.|
|003 Sizing|Integer targets and weighted average basis. Include entry fees in basis and exit fees in realised P&L.|FIFO needs a lot ledger. Closed-trade analytics will group flat-to-flat cycles.|Partial sale golden fixture.|
|004 Precision|Binary64 accounting and strict nonnegative post-fill cash. Decimal oracle in tests.|Integer minor units would require an explicit tick, currency and fee rounding policy.|Check cash with relative tolerance 1e-12 and absolute tolerance 1e-11 on small fixtures. Exact order outcomes at tested boundaries. Extreme magnitudes and near-threshold decimal differences remain audit risks.|
|005 Second engine|Independently implement ledger and array signals in M4.|Shared accounting would conceal shared defects.|Future comparison of every fill, rejection and mark.|
|006 Data|Strict schema, explicit zones, optional supplied schedule, file hashes.|Silently filling missing bars invents prices.|CSV/Parquet, invalid inputs, DST, schedule tests.|
|007 Analytics|Elapsed time for CAGR, explicit frequency for annualisation; chronological selection.|Hard-coded 252 mishandles other clocks.|M3 manual fixtures; M5 held-out folds.|

## Accounting and strategy
For signed quantity d, fill price is open times (1 + sign(d) times slip). Fee is fixed + abs(d) times price times rate. New cash equals old cash minus d times price minus fee. Equity equals cash plus marked inventory. The other independent identity is initial cash plus realised and unrealised profit. No forced final sale.

Buy-and-hold requests size units at every close, including the first. SMA requires a full slow window and goes long when the short mean exceeds the long mean, otherwise flat. Equality is flat. Both retry a target after a rejection. SMA uses rolling sums, O(n) time and O(slow) indicator memory. Floating-point cancellation can change a near-equal crossover. Buy-and-hold may repeatedly request an unaffordable size. Whipsaws can make SMA sensitive to costs. Audit histories and the eager loader use O(n) memory.

## Interview checks
1. Why does a close-derived target need both a decision timestamp and an execution timestamp?
2. How can a calendar gap change the meaning of next open?
3. Derive the realised and remaining unrealised profit after selling half the position.
4. Give an input for which an epsilon-based cash check would introduce leverage.
5. Why does prefix invariance catch future leakage, and which external data leaks can it miss?
