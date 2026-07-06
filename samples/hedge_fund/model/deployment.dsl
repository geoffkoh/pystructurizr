// Production deployment: latency-sensitive execution in a colo, the rest in AWS.

deploymentEnvironment "Production" {

    deploymentNode "Equinix NY4" "Colocation facility adjacent to major venues" "Colo cage" {
        deploymentNode "Trading Server A" "Low-latency execution host" "Bare metal, RHEL 9, kernel-bypass NIC" {
            algoInst = containerInstance algoEngine
            sorInst  = containerInstance sor
        }
        deploymentNode "Gateway Server" "Venue connectivity host" "Bare metal, RHEL 9" {
            fixInst = containerInstance fixGateway
        }
        deploymentNode "Market Data Server" "Feed capture host" "Bare metal, RHEL 9" {
            feedInst = containerInstance feedHandler
            busInst  = containerInstance mdBus
        }
        venueCross = infrastructureNode "Venue Cross-Connects" "Direct fibre to exchange matching engines" "Fibre cross-connect"
    }

    deploymentNode "AWS us-east-1" "Primary cloud region" "Amazon Web Services" {
        deploymentNode "EKS Cluster" "Middle- and back-office workloads" "Kubernetes 1.31" {
            deploymentNode "oms namespace" "" "Kubernetes namespace" {
                orderSvcInst   = containerInstance orderSvc
                complianceInst = containerInstance complianceEngine
                positionInst   = containerInstance positionSvc
            }
            deploymentNode "risk namespace" "" "Kubernetes namespace" {
                riskEngineInst = containerInstance riskEngine
                varInst        = containerInstance varSvc
                pnlInst        = containerInstance pnlSvc
            }
        }
        deploymentNode "RDS" "Managed PostgreSQL" "db.r6g.2xlarge, Multi-AZ" {
            omsDbInst = containerInstance omsDb
        }
        deploymentNode "Timestream Cluster" "Managed time-series storage" "TimescaleDB on EC2" {
            riskStoreInst = containerInstance riskStore
        }
        alb = infrastructureNode "Application Load Balancer" "Terminates TLS for internal UIs and APIs" "AWS ALB"
        dx  = infrastructureNode "Direct Connect" "Private link between AWS and the colo" "10 Gbps AWS Direct Connect"
    }

    // Deployment-level plumbing between infrastructure and instances.
    alb -> orderSvcInst "Routes API traffic to" "HTTPS"
    dx  -> busInst "Extends market data bus over" "Aeron/UDP"
    fixInst -> venueCross "Sends orders via"
}
