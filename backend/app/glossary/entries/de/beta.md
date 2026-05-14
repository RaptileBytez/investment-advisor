---
key: beta
title: Beta (β)
short: Wie stark eine Aktie relativ zum Markt schwankt — β=1 bedeutet im Gleichschritt mit dem Markt.
related: [volatility, sharpe-ratio]
---

**Beta** misst, wie empfindlich die Renditen einer Aktie auf ihren
Benchmark reagieren (z. B. S&P 500 für US-Aktien, DAX für deutsche
Aktien).

$$
\beta = \frac{\text{Cov}(R_\text{Aktie}, R_\text{Markt})}{\text{Var}(R_\text{Markt})}
$$

### Interpretation

- **β = 1,0** — bewegt sich im Gleichschritt mit dem Markt.
- **β > 1,0** — verstärkt Marktbewegungen. β = 1,5 bedeutet ca. +15 %,
  wenn der Markt +10 % macht, und -15 % bei einem Marktrückgang von 10 %.
- **β = 0** — unkorreliert zum Markt (bei Aktien selten).
- **β < 0** — bewegt sich gegenläufig (ebenfalls selten; z. B. einige
  Goldminenwerte).

### Warum Benchmarks wichtig sind

Beta ist ohne den *richtigen* Benchmark wertlos. Beta von **SAP.DE**
gegen den S&P 500 zu berechnen mischt zwei verschiedene Märkte und liefert
Rauschen. Dieser Berater wählt automatisch den **regionalen Benchmark**:

| Region      | Benchmark      |
| ----------- | -------------- |
| USA         | S&P 500        |
| Deutschland | DAX            |
| Frankreich  | CAC 40         |
| UK          | FTSE 100       |
| Japan       | Nikkei 225     |

### Grenzen

- Beta ist eine historische Schätzung — sie kann sich verschieben,
  insbesondere bei Gewinnveränderungen oder Sektorrotationen.
- Es erfasst Marktrisiko, aber kein unternehmensspezifisches Risiko.
  Volatilität und Max. Drawdown decken dies ab.
