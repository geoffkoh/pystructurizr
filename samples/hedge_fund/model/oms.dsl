// Order Management System: order raising, compliance, allocations.

oms = softwareSystem "Order Management System" "Order lifecycle from portfolio decision to allocation, with pre-trade compliance" {
    omsUi = container "Order Blotter" "Order entry and lifecycle monitoring for PMs" "React, TypeScript"

    orderSvc = container "Order Service" "Owns the parent order lifecycle and allocations" "Java, Spring Boot" {
        orderApi     = component "Order API" "REST/gRPC entry point for order actions" "Spring MVC"
        validator    = component "Order Validator" "Sanity-checks instrument, quantity and limit price" "Java"
        limitChecker = component "Pre-Trade Check Adapter" "Requests mandate and restriction checks" "Java"
        lifecycle    = component "Lifecycle State Machine" "Order state transitions with full audit trail" "Java"
        allocEngine  = component "Allocation Engine" "Splits fills across funds and managed accounts" "Java"
        orderRepo    = component "Order Repository" "Persistence for orders, fills and allocations" "JPA, Hibernate"
    }

    complianceEngine = container "Compliance Engine" "Pre- and post-trade rule evaluation against mandates and restricted lists" "Java, Drools"
    positionSvc      = container "Position Service" "Real-time positions and cash built from fills and settlements" "Kotlin"
    omsDb            = container "OMS Database" "Orders, fills, allocations and audit history" "PostgreSQL"
}
