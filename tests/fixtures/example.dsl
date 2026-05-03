workspace "Internet Banking" "Example C4 workspace" {

    model {
        customer = person "Personal Banking Customer" "A customer of the bank"
        bank = softwareSystem "Internet Banking System" "Allows customers to view information" {
            webapp = container "Web Application" "Serves static content" "Java, Spring MVC"
            spa = container "Single-Page App" "Provides banking UI" "JavaScript, Angular"
            api = container "API Application" "Provides internet banking API" "Java, Spring Boot"
            db = container "Database" "Stores user data" "Oracle"
        }
        email = softwareSystem "E-mail System" "External e-mail" "External System"
        mainframe = softwareSystem "Mainframe Banking System" "Core banking" "External System"

        customer -> spa "Uses"
        customer -> webapp "Visits" "HTTPS"
        webapp -> spa "Delivers"
        spa -> api "Makes API calls" "JSON/HTTPS"
        api -> db "Reads/writes" "JDBC"
        api -> email "Sends e-mails" "SMTP"
        api -> mainframe "Makes API calls" "XML/HTTPS"
        email -> customer "Sends emails to"
    }

    views {
        systemContext bank SystemContext {
            include *
            autoLayout
        }

        container bank Containers {
            include *
            autoLayout
        }
    }
}
