// Market data ingestion and distribution.

marketData = softwareSystem "Market Data Platform" "Ingests, normalises and distributes real-time and historical market data" {
    feedHandler = container "Feed Handlers" "Vendor- and venue-specific feed ingestion and normalisation" "C++"
    mdBus       = container "Market Data Bus" "Low-latency distribution of normalised ticks" "Aeron"
    tickStore   = container "Tick Store" "Historical tick and bar data for research and TCA" "kdb+"
    refData     = container "Reference Data Service" "Instrument master, trading calendars and corporate actions" "Java, Spring Boot"
}
