# Order flow

The *Dynamic – Order placement and execution* view animates the full path:

1. A portfolio manager raises a parent order in the order blotter.
2. The order service validates it and runs pre-trade compliance.
3. Accepted orders are staged to the algo engine, which slices them
   against a VWAP/TWAP schedule.
4. Child orders pass the pre-trade risk gate, are routed by the smart
   order router, and execute on venues over FIX.
5. Fills flow back to the order lifecycle and on to positions and risk.

> Compliance evaluates every parent order **before** it leaves the OMS;
> the risk gate re-checks every child order in the hot path.
