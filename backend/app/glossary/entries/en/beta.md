---
key: beta
title: Beta (β)
short: How much a stock moves relative to its benchmark — β=1 means in line with the market.
related: [volatility, sharpe-ratio]
---

**Beta** measures how sensitive a stock's returns are to its benchmark
(e.g. the S&P 500 for US stocks, the DAX for German stocks).

$$
\beta = \frac{\text{Cov}(R_\text{stock}, R_\text{market})}{\text{Var}(R_\text{market})}
$$

### Interpretation

- **β = 1.0** — moves in line with the market.
- **β > 1.0** — amplifies the market. β = 1.5 means roughly +15 % when the
  market moves +10 %, and -15 % when it falls 10 %.
- **β = 0** — uncorrelated to the market (rare for equities).
- **β < 0** — moves opposite to the market (also rare; some gold miners).

### Why benchmarks matter

Beta is meaningless without the *right* benchmark. Computing beta of
**SAP.DE** against the S&P 500 mixes two different markets and produces
noise. This advisor pairs each ticker with its **region's benchmark**:

| Region   | Benchmark             |
| -------- | --------------------- |
| US       | S&P 500               |
| Germany  | DAX                   |
| France   | CAC 40                |
| UK       | FTSE 100              |
| Japan    | Nikkei 225            |

### Limitations

- Beta is a historical estimate — it can shift, especially around earnings
  changes or sector rotations.
- It captures market risk but not idiosyncratic risk (company-specific
  events). Volatility and Max Drawdown cover that.
