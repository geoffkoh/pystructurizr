workspace "E-Commerce Platform" "Microservices-based online retail system" {

    model {
        shopper  = person "Shopper" "A customer browsing and purchasing products"
        merchant = person "Merchant" "A seller managing products and orders"
        admin    = person "Platform Admin" "Manages the platform, monitors health"

        ecommerce = softwareSystem "E-Commerce Platform" "Core online retail platform" {
            storefront  = container "Storefront" "Server-rendered product catalogue and checkout" "Next.js"
            adminPanel  = container "Admin Panel" "Merchant and platform management UI" "React, Vite"

            catalog     = container "Catalog Service" "Product listings, search, categories" "Go"
            cart        = container "Cart Service" "Shopping cart and session management" "Node.js"
            orders      = container "Order Service" "Order lifecycle management" "Python, FastAPI"
            payments    = container "Payment Service" "Charge processing and refunds" "Java, Spring Boot"
            inventory   = container "Inventory Service" "Stock levels and reservations" "Go"
            notifications = container "Notification Service" "Order and shipping emails/SMS" "Python"

            catalogDb   = container "Catalog DB" "Product data" "PostgreSQL"
            ordersDb    = container "Orders DB" "Order records" "PostgreSQL"
            cartCache   = container "Cart Cache" "Session and cart data" "Redis"
            messageBus  = container "Message Bus" "Async event streaming between services" "Kafka"
        }

        paymentGateway = softwareSystem "Payment Gateway" "Stripe – card processing" "External System"
        shippingApi    = softwareSystem "Shipping API" "FedEx – shipment tracking" "External System"
        emailProvider  = softwareSystem "E-mail Provider" "Mailgun – transactional email" "External System"

        shopper  -> storefront "Browses and purchases" "HTTPS"
        merchant -> adminPanel "Manages listings and orders" "HTTPS"
        admin    -> adminPanel "Monitors platform" "HTTPS"

        storefront -> catalog     "Fetches products" "gRPC"
        storefront -> cart        "Manages cart" "REST/HTTPS"
        storefront -> orders      "Places orders" "REST/HTTPS"
        adminPanel -> catalog     "Creates/edits products" "REST/HTTPS"
        adminPanel -> orders      "Views and manages orders" "REST/HTTPS"
        adminPanel -> inventory   "Adjusts stock" "REST/HTTPS"

        catalog   -> catalogDb   "Reads/writes" "SQL"
        orders    -> ordersDb    "Reads/writes" "SQL"
        cart      -> cartCache   "Reads/writes" "Redis protocol"

        orders    -> messageBus  "Publishes OrderPlaced events"
        payments  -> messageBus  "Publishes PaymentProcessed events"
        inventory -> messageBus  "Consumes OrderPlaced events"
        notifications -> messageBus "Consumes events"

        payments  -> paymentGateway "Charges cards" "REST/HTTPS"
        orders    -> shippingApi    "Books shipments" "REST/HTTPS"
        notifications -> emailProvider "Sends email" "SMTP"
    }

    views {
        systemContext ecommerce EcommerceContext "E-Commerce – System Context" {
            include *
            autoLayout
        }

        container ecommerce EcommerceContainers "E-Commerce – Containers" {
            include *
            autoLayout
        }
    }
}
