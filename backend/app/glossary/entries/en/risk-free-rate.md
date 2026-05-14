---
key: risk-free-rate
title: Risk-free rate
short: The return on an essentially-default-free short-term bond (e.g. T-bill).
related: [sharpe-ratio]
---

The **risk-free rate** is the return you could earn without taking on
default risk. In practice, we use short-dated government debt as a proxy:

- USD assets → US 13-week T-bill (^IRX on yfinance).
- EUR assets → ECB short rate (€STR / deposit-facility).
- GBP assets → Bank of England base rate.

It's the baseline that all risky returns must clear to be worth holding.
If a stock returns 8 % p.a. and risk-free is 5 %, the *excess* return
worth analysing is 3 %. The **Sharpe Ratio** is built on this excess.

### Why region matters

A US T-bill yield is irrelevant to a euro-denominated portfolio — the
investor doesn't actually have access to that return without FX risk.
This advisor picks the region-appropriate rate for every ticker based on
its listing exchange.
