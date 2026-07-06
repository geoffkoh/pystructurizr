// Execution Management System: algos, routing and venue connectivity.

ems = softwareSystem "Execution Management System" "Algorithmic execution, smart order routing and broker/venue connectivity" {
    execUi     = container "Execution Blotter" "Trader UI for working orders and steering algos" "React, TypeScript"

    algoEngine = container "Algo Engine" "VWAP/TWAP/POV execution algorithms over parent orders" "C++" {
        parentOrders = component "Parent Order Manager" "Tracks parent orders staged from the OMS" "C++"
        scheduler    = component "Execution Scheduler" "Builds VWAP/TWAP/POV slice schedules" "C++"
        childOrders  = component "Child Order Manager" "Manages child order state and re-slicing" "C++"
        mdAdapter    = component "Market Data Adapter" "Subscribes to normalised ticks and volume curves" "C++, Aeron client"
        riskGate     = component "Pre-Trade Risk Gate" "Fat-finger and exposure limits before routing" "C++"
    }

    sor        = container "Smart Order Router" "Venue selection and child-order slicing" "C++"
    fixGateway = container "FIX Gateway" "Session management for broker and venue FIX connectivity" "C++, QuickFIX"
    tca        = container "TCA Service" "Post-trade transaction cost analysis and benchmarking" "Python"
    execStore  = container "Execution Store" "Child orders, routes and executions" "PostgreSQL" "Database"
}
