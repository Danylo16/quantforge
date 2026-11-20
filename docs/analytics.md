# Quantitative analytics
Every backtest emits metrics.json. Values are binary64 fractions; null entries have a reason in undefined. Annual volatility and risk ratios require an explicit --periods-per-year for regularly sampled sessions. The caller supplies that frequency, including when a trading calendar omits weekends. For irregular intervals omit the frequency. --risk-free is an annual effective fraction, default zero.

For equity E, simple return r is the change divided by previous equity. Total return is last equity divided by initial equity minus one. CAGR compounds that ratio over elapsed UTC time using 365.2425 days per year. Maximum drawdown is the greatest fractional decline from a running peak (positive loss magnitude). Calmar divides CAGR by maximum drawdown.

With F periods per year, volatility is sample standard deviation of r times sqrt(F). Subtract expm1(log1p(risk_free)/F) from each return for excess returns x. Sharpe divides mean(x) times sqrt(F) by sample standard deviation of r. Sortino replaces the denominator with sqrt(mean(min(x,0)^2)), including all periods. Single returns cannot estimate sample volatility.

Exposure averages invested value / equity across bar closes, including the first. Gross turnover sums absolute fill notionals and divides by average close equity. Closed trades are flat-to-flat cycles. P&L includes all entry and exit fees. Trade return divides net P&L by cumulative purchase costs. Win rate counts strictly profitable cycles; profit factor divides gross wins by absolute gross losses. Open positions contribute to equity and exposure.

Momentum takes the long target when the current close exceeds the close L bars earlier. Mean reversion takes the long target when the close falls below the arithmetic mean of the preceding L closes. Both use --slow as L and stay flat for the first L closes and on equality. Mean reversion uses an accurate sum of its window, O(L) time per bar. Momentum costs O(1). Both use O(L) state.

Interview checks: Why can total return be zero with positive mean returns? How does a partial exit change trade count? Why can CAGR on a short sample overflow?
