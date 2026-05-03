workspace "SaaS Monitoring Platform" "A multi-tenant observability platform with agents, ingestion, and dashboards" {

    model {
        devops    = person "DevOps Engineer" "Configures monitors, views dashboards, responds to alerts"
        developer = person "Application Developer" "Instruments applications and reviews traces"
        oncall    = person "On-Call Engineer" "Responds to pages triggered by the platform"

        monitoring = softwareSystem "Monitoring Platform" "Collects metrics, logs, and traces; alerts on anomalies" {
            agentSDK    = container "Agent / SDK" "Collects metrics, traces, and logs from instrumented apps" "Go, OpenTelemetry"
            ingestApi   = container "Ingest API" "Receives telemetry data at scale" "Go, gRPC+HTTP"
            pipeline    = container "Processing Pipeline" "Normalises, enriches, and routes telemetry" "Apache Flink"
            metricsStore = container "Metrics Store" "Long-term time-series storage" "ClickHouse"
            logStore    = container "Log Store" "Full-text searchable log archive" "OpenSearch"
            traceStore  = container "Trace Store" "Distributed trace storage" "Apache Cassandra"
            rulesEngine = container "Rules & Alerting Engine" "Evaluates alert conditions and fires notifications" "Python"
            queryApi    = container "Query API" "Serves dashboard and search queries" "Python, FastAPI"
            dashboard   = container "Dashboard UI" "Web-based visualisation and alerting UI" "TypeScript, React"
            configApi   = container "Config API" "Manages monitors, alert rules, teams" "Go"
        }

        pagerduty = softwareSystem "PagerDuty" "Incident management and on-call scheduling" "External System"
        slack     = softwareSystem "Slack" "Team communication and alert notifications" "External System"
        smtp      = softwareSystem "E-mail (SMTP)" "Alert delivery via e-mail" "External System"

        // user flows
        devops    -> dashboard  "Configures dashboards and alert rules"
        developer -> dashboard  "Views traces and logs"
        oncall    -> dashboard  "Investigates incidents"

        devops    -> configApi  "Manages monitors via API" "REST/HTTPS"

        // data ingestion
        agentSDK  -> ingestApi  "Streams telemetry" "gRPC/HTTPS"
        ingestApi -> pipeline   "Publishes events" "Kafka"

        pipeline  -> metricsStore "Writes metrics"  "ClickHouse TCP"
        pipeline  -> logStore     "Writes log lines" "HTTP bulk"
        pipeline  -> traceStore   "Writes spans"     "CQL"
        pipeline  -> rulesEngine  "Forwards aggregated metrics" "Kafka"

        // query path
        dashboard -> queryApi    "Fetches chart data" "REST/HTTPS"
        queryApi  -> metricsStore "Queries metrics"   "SQL"
        queryApi  -> logStore     "Searches logs"     "REST"
        queryApi  -> traceStore   "Retrieves traces"  "CQL"

        // alerting
        rulesEngine -> pagerduty "Creates incidents"       "REST/HTTPS"
        rulesEngine -> slack     "Posts alert messages"    "Webhooks/HTTPS"
        rulesEngine -> smtp      "Sends alert emails"      "SMTP"
        pagerduty   -> oncall    "Pages on-call engineer"
    }

    views {
        systemContext monitoring MonitoringContext "Monitoring Platform – System Context" {
            include *
            autoLayout
        }

        container monitoring MonitoringContainers "Monitoring Platform – Containers" {
            include *
            autoLayout
        }
    }
}
