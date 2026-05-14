---
key: sharpe-ratio
title: Sharpe Ratio
short: Risikoadjustierte Rendite — wie viel Mehrertrag pro Einheit Volatilität.
related: [volatility, risk-free-rate, beta]
---

Die **Sharpe Ratio** beantwortet die Frage: *„Wie viel Mehrertrag habe ich
pro Risiko-Einheit gegenüber einer risikofreien Anlage erzielt?"*

$$
\text{Sharpe} = \frac{\overline{R_p} - R_f}{\sigma_p} \times \sqrt{N}
$$

mit $\overline{R_p}$ als durchschnittlicher Rendite, $R_f$ als
**risikofreiem Zins**, $\sigma_p$ als Volatilität und $N$ zur
Annualisierung.

### Interpretation

| Sharpe | Bedeutung                                          |
| ------ | -------------------------------------------------- |
| < 0    | Schlechter als eine risikofreie Anlage.            |
| 0 – 1  | Akzeptabel, aber nicht beeindruckend.              |
| 1 – 2  | Gut — typisch für gut diversifizierte Portfolios.  |
| > 2    | Hervorragend (und oft schwer dauerhaft zu halten). |

### Einschränkungen

- Sharpe bestraft **jede** Volatilität, auch nach oben. Aktien mit
  positiven Sprüngen können schlechter aussehen, als sie sind.
- Empfindlich gegenüber dem gewählten risikofreien Zins — wir verwenden
  einen regionsabhängigen Kurzzeitzins (z. B. US-T-Bill für USD, Fallback
  für EUR).
- Vergleiche Äpfel mit Äpfeln: Sharpe einer Aktie vs. eines breiten Index
  ist aussagekräftiger, wenn beide den gleichen Zeitraum verwenden.
