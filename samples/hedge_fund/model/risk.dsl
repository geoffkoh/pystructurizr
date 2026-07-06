// Intraday risk, limits and P&L.

risk = softwareSystem "Risk & PnL Platform" "Intraday exposures, VaR, limits and P&L attribution" {
    riskEngine = container "Real-Time Risk Engine" "Streams positions and prices into exposures and Greeks" "Java"
    varSvc     = container "VaR Service" "Historical-simulation VaR and stress testing" "Python, NumPy"
    pnlSvc     = container "PnL Service" "Live and end-of-day P&L attribution" "Kotlin"
    riskUi     = container "Risk Dashboard" "Limits, exposures and drawdown monitoring" "React, TypeScript"
    riskStore  = container "Risk Store" "Time-series of exposures, VaR results and P&L" "TimescaleDB" "Database"
}
