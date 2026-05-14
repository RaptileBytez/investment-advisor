---
key: sharpe-ratio
title: Sharpe Ratio
short: Risk-adjusted return — how much extra return you got per unit of volatility.
related: [volatility, risk-free-rate, beta]
---

The **Sharpe Ratio** answers: *"For each unit of risk I took, how much
extra return did I earn over a risk-free asset?"*

$$
\text{Sharpe} = \frac{\overline{R_p} - R_f}{\sigma_p} \times \sqrt{N}
$$

where $\overline{R_p}$ is the asset's average return, $R_f$ is the
**risk-free rate**, $\sigma_p$ is its volatility, and $N$ annualises it.

### How to read it

| Sharpe | Interpretation                                    |
| ------ | ------------------------------------------------- |
| < 0    | Underperformed a risk-free asset (bad).           |
| 0 – 1  | Acceptable, but not impressive.                   |
| 1 – 2  | Good — typical for well-diversified portfolios.   |
| > 2    | Excellent (and often hard to sustain).            |

### Caveats

- Sharpe penalises **all** volatility, including upside. Stocks that pop
  unpredictably can look worse than they are.
- It's sensitive to the chosen risk-free rate — we use a region-appropriate
  short-rate (e.g. US T-bills for USD, fallback for EUR).
- Compare apples-to-apples: Sharpe of a stock vs. a broad index is more
  meaningful when both use the same period.
