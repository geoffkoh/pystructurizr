workspace "Quantia Capital Trading Platform" "Front-to-back trading architecture for a systematic hedge fund" {

    model {
        !include model/people.dsl
        !include model/market_data.dsl
        !include model/oms.dsl
        !include model/ems.dsl
        !include model/risk.dsl
        !include model/externals.dsl
        !include model/relationships.dsl
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

        container marketData MarketDataContainers "Market Data – Containers" {
            include *
            autoLayout
        }

        container risk RiskContainers "Risk & PnL – Containers" {
            include *
            autoLayout
        }
    }
}
