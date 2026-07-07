# Overview

Quantia Capital's trading platform covers the full order lifecycle for a
systematic hedge fund: portfolio construction signals become parent orders
in the **Order Management System**, are executed algorithmically by the
**Execution Management System**, and are monitored in real time by the
**Risk & PnL Platform**, all fed by a low-latency **Market Data Platform**.

| System | Responsibility | Latency profile |
| --- | --- | --- |
| Order Management | Order lifecycle, compliance, allocations | Milliseconds |
| Execution Management | Algos, routing, venue connectivity | Microseconds |
| Market Data | Ingestion, normalisation, distribution | Microseconds |
| Risk & PnL | Exposures, VaR, P&L attribution | Seconds |

Start from the **Landscape** view and drill down: double-click a system for
its context, again for containers, and again for components.
