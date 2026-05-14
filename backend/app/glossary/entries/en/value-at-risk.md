---
key: value-at-risk
title: Value at Risk (VaR 95 %)
short: The worst expected one-day loss in 95 out of 100 days.
related: [volatility, max-drawdown]
---

**VaR 95 %** answers: *"On the worst 5 % of days, how much could I lose
in a single day?"*

We compute it by the *historical method*: sort all the daily returns,
take the 5th percentile, and flip the sign.

### Example

A VaR of **3 %** means: on 95 of 100 typical days, your loss should be
less than 3 %. On the *other* 5 days, losses can — and historically
have — gone deeper than that. **VaR is not a worst case.** It's a
threshold.

### Why use it

- Easy to communicate to non-quants: *"a 1 % position has a 1-day VaR of
  roughly 3 % × 1 % = 0.03 % of the portfolio."*
- Cleaner than volatility for someone asking *"what's the worst typical
  day?"* — volatility is a width, VaR is a tail.

### Caveats

- **Tail risk lives beyond VaR.** It tells you what 95 % of days look
  like; it says nothing about how bad the other 5 % can get. Use Max
  Drawdown for that.
- Sensitive to the lookback period. A short window underestimates
  long-tail events that haven't happened recently.
