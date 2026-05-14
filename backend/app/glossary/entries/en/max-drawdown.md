---
key: max-drawdown
title: Maximum Drawdown
short: The biggest peak-to-trough decline ever observed.
related: [volatility, value-at-risk]
---

**Max Drawdown** is the largest percentage drop from a previous all-time
high to a subsequent low, over the analysis window.

### Why it matters

Volatility tells you how *bumpy* the ride is on average. Max drawdown
tells you how *bad* it has actually gotten — the worst single moment a
holder of this asset would have endured.

It's the metric to look at if you're asking yourself:
> *"If the market repeats its worst stretch, how much could I lose before
> it recovers?"*

### Example

A series that ran 100 → 130 → 60 → 90 has a max drawdown of
**(60 - 130) / 130 = -53.8 %**. Even if the eventual return looks fine,
holders would have needed to stomach a > 50 % paper loss.

### How to use it

- Compare across stocks: a 30 % CAGR with -70 % max DD is a very
  different proposition than 15 % CAGR with -25 % max DD.
- Pair with **Recovery Time** (not yet shown in the UI) — a -50 % DD that
  recovers in a year is gentler than the same DD that takes a decade.
