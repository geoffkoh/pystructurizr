workspace "Quantia Capital Trading Platform" "Front-to-back trading architecture for a systematic hedge fund" {

    model {
        !include model/people.dsl
        !include model/market_data.dsl
        !include model/oms.dsl
        !include model/ems.dsl
        !include model/risk.dsl
        !include model/externals.dsl
        !include model/relationships.dsl
        !include model/deployment.dsl
    }

    views {
        systemContext oms OmsContext "Order Management – System Context" {
            include *
            autoLayout
        }

        container oms OmsContainers "Order Management – Containers" {
            include *
            autoLayout
        }

        component orderSvc OrderServiceComponents "Order Service – Components" {
            include *
            autoLayout
        }

        systemContext ems EmsContext "Execution – System Context" {
            include *
            autoLayout
        }

        container ems EmsContainers "Execution – Containers" {
            include *
            autoLayout
        }

        component algoEngine AlgoEngineComponents "Algo Engine – Components" {
            include *
            autoLayout lr
        }

        container marketData MarketDataContainers "Market Data – Containers" {
            include *
            autoLayout
        }

        container risk RiskContainers "Risk & PnL – Containers" {
            include *
            autoLayout
        }

        deployment * "Production" ProductionDeployment "Production – Full Estate" {
            include *
            autoLayout
        }

        deployment oms "Production" OmsProduction "Order Management – Production Deployment" {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                background #08427b
                shape Person
            }
            element "External System" {
                background #8a94a6
                color #ffffff
            }
            element "Database" {
                shape Cylinder
            }
        }
    }
}
