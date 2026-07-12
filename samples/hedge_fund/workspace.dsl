workspace "Quantia Capital Trading Platform" "Front-to-back trading architecture for a systematic hedge fund" {

    !docs docs
    !adrs adrs

    model {
        enterprise "Quantia Capital"

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
        // AWS service logos for the deployment views (icons load lazily;
        // offline sessions simply render without them).
        theme "https://static.structurizr.com/themes/amazon-web-services-2023.01.31/theme.json"

        systemLandscape Landscape "Quantia – System Landscape" {
            include *
            autoLayout
        }

        filtered Landscape exclude "External System" InternalOnly "Quantia – Internal Systems"

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

        dynamic oms PlaceOrder "Dynamic – Order placement and execution" {
            pm -> omsUi "Raises a parent order"
            omsUi -> orderApi "Submits the order" "JSON/HTTPS"
            orderApi -> validator "Validates instrument and quantity"
            validator -> limitChecker "Requests pre-trade checks"
            limitChecker -> complianceEngine "Evaluates mandates and restrictions"
            orderApi -> lifecycle "Accepts and books the order"
            lifecycle -> parentOrders "Stages the parent order to the EMS"
            scheduler -> childOrders "Slices the order over the schedule"
            riskGate -> sor "Releases child orders"
            sor -> fixGateway "Routes to the best venue"
            fixGateway -> venues "Executes on venue"
            fixGateway -> lifecycle "Reports fills back"
            autoLayout lr
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
