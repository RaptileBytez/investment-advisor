---
key: risk-free-rate
title: Risikofreier Zins
short: Die Rendite einer praktisch ausfallfreien kurzlaufenden Anleihe (z. B. T-Bill).
related: [sharpe-ratio]
---

Der **risikofreie Zins** ist die Rendite, die du ohne Ausfallrisiko
verdienen kannst. In der Praxis verwenden wir kurzlaufende
Staatsanleihen als Proxy:

- USD-Anlagen → 13-Wochen US-T-Bill (^IRX auf yfinance).
- EUR-Anlagen → EZB-Kurzfristzins (€STR / Einlagefazilität).
- GBP-Anlagen → Bank of England Leitzins.

Es ist die Basis, die alle riskanten Renditen schlagen müssen, um sich
zu lohnen. Wenn eine Aktie 8 % p.a. bringt und der risikofreie Zins
5 % beträgt, ist die *Mehrrendite* von 3 % der wirklich
interessante Wert. Die **Sharpe Ratio** baut auf dieser Mehrrendite auf.

### Warum die Region zählt

Eine US-T-Bill-Rendite ist für ein in Euro denominiertes Portfolio
irrelevant — der Anleger hat ohne Währungsrisiko gar keinen Zugriff
darauf. Dieser Berater wählt automatisch den passenden Zins basierend
auf dem Listing der Aktie.
