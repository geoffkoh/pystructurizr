workspace "Internet Banking System" "A classic C4 example: online banking platform" {

    model {
        customer = person "Personal Banking Customer" "A customer of the bank with personal accounts"
        staff    = person "Customer Service Staff" "Internal staff handling customer queries"

        banking = softwareSystem "Internet Banking System" "Allows customers to view account info, make payments, and manage finances online" {
            webApp    = container "Web Application" "Delivers the static SPA to the browser" "Java, Spring MVC"
            spa       = container "Single-Page Application" "Provides all banking functionality in the browser" "TypeScript, Angular"
            mobileApp = container "Mobile App" "Provides a subset of banking functionality via iOS/Android" "Kotlin, Swift"
            apiGateway = container "API Gateway" "Routes and authenticates API calls" "Kong"
            accountsApi = container "Accounts API" "Handles account queries and history" "Java, Spring Boot"
            paymentsApi = container "Payments API" "Processes payments and transfers" "Java, Spring Boot"
            notifService = container "Notification Service" "Sends email and push notifications" "Python, FastAPI"
            db = container "Accounts Database" "Stores account and transaction data" "PostgreSQL"
        }

        email     = softwareSystem "E-mail System" "SendGrid – external e-mail delivery" "External System"
        mainframe = softwareSystem "Mainframe Banking System" "Stores core account and transaction records" "External System"

        // user interactions
        customer -> webApp    "Visits" "HTTPS"
        customer -> mobileApp "Uses"
        staff    -> spa        "Uses for customer support"

        webApp -> spa "Serves"

        spa        -> apiGateway "Calls" "JSON/HTTPS"
        mobileApp  -> apiGateway "Calls" "JSON/HTTPS"
        apiGateway -> accountsApi "Routes to" "JSON/HTTPS"
        apiGateway -> paymentsApi "Routes to" "JSON/HTTPS"

        accountsApi -> db          "Reads/writes" "JDBC"
        paymentsApi -> db          "Reads/writes" "JDBC"
        paymentsApi -> mainframe   "Submits transactions" "ISO 20022/HTTPS"
        paymentsApi -> notifService "Publishes payment events" "AMQP"

        notifService -> email    "Sends e-mails via" "SMTP"
        email        -> customer "Delivers notifications to"
    }

    views {
        systemContext banking SystemContext "Internet Banking – System Context" {
            include *
            autoLayout
        }

        container banking Containers "Internet Banking – Containers" {
            include *
            autoLayout
        }
    }
}
