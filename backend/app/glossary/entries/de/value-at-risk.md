---
key: value-at-risk
title: Value at Risk (VaR 95 %)
short: Der schlechteste erwartete Tagesverlust in 95 von 100 Tagen.
related: [volatility, max-drawdown]
---

**VaR 95 %** beantwortet die Frage: *„Wie viel könnte ich an den
schlechtesten 5 % der Tage an einem einzigen Tag verlieren?"*

Wir berechnen ihn mit der *historischen Methode*: alle Tagesrenditen
sortieren, das 5. Perzentil nehmen, Vorzeichen drehen.

### Beispiel

Ein VaR von **3 %** bedeutet: an 95 von 100 typischen Tagen sollte
dein Verlust kleiner als 3 % sein. An den *anderen* 5 Tagen können —
und sind historisch — die Verluste größer ausgefallen. **VaR ist
nicht der Worst Case.** Es ist eine Schwelle.

### Einsatz

- Gut kommunizierbar: *„Eine 1 %-Position hat einen 1-Tages-VaR von
  etwa 3 % × 1 % = 0,03 % des Portfolios."*
- Klarer als Volatilität bei der Frage *„Was ist der schlechteste
  typische Tag?"* — Volatilität ist eine Breite, VaR ein Schwanz.

### Einschränkungen

- **Extremrisiko liegt jenseits des VaR.** Er sagt, wie 95 % der Tage
  aussehen; er sagt nichts über die übrigen 5 %. Dafür ist Max.
  Drawdown da.
- Empfindlich gegenüber dem Beobachtungszeitraum. Ein kurzes Fenster
  unterschätzt seltene Extremereignisse.
