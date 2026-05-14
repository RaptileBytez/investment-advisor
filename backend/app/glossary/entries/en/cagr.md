---
key: cagr
title: CAGR
short: Compound Annual Growth Rate — the smoothed annual return over a period.
related: [volatility, sharpe-ratio]
---

**CAGR** is the constant annual rate of return that would take an
investment from its starting value to its ending value over a given
period, *if* it grew steadily.

$$
\text{CAGR} = \left( \frac{V_\text{end}}{V_\text{start}} \right)^{1/n} - 1
$$

where $n$ is the number of years.

### Example

Buy at 100, sell at 200 after 5 years → CAGR = 2^(1/5) − 1 ≈ **14.87 %**.

### Why use it

- Strips out the year-by-year noise so two assets with very different
  paths but the same start/end values get the same CAGR.
- Handy for comparing stocks over identical periods.

### What it *doesn't* tell you

CAGR is a smooth average — the real path could have been a bumpy ride.
Two assets with identical CAGR can have wildly different Max Drawdown
and Sharpe. Look at all three together.
