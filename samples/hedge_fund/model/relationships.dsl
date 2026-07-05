// Relationships, declared at the most specific level the model knows.
// Coarser views (context/container) lift these to the visible ancestor.

// --- People ---
pm         -> omsUi "Raises and monitors orders with"
trader     -> execUi "Works orders and steers algos with"
quant      -> tickStore "Backtests signals and cost models against"
riskMgr    -> riskUi "Monitors limits and exposures in"
compliance -> complianceEngine "Maintains mandates and restricted lists in"
opsAnalyst -> positionSvc "Reconciles positions and breaks with"

// --- Order Management internals ---
omsUi        -> orderApi "Submits order actions to" "JSON/HTTPS"
orderApi     -> validator "Passes new orders to"
validator    -> limitChecker "Requests pre-trade checks from"
limitChecker -> complianceEngine "Evaluates mandate rules via" "gRPC"
orderApi     -> lifecycle "Applies accepted actions to"
lifecycle    -> orderRepo "Persists state transitions via"
allocEngine  -> orderRepo "Records allocations via"
orderRepo    -> omsDb "Reads/writes" "JDBC"
positionSvc  -> omsDb "Builds positions from fills in" "JDBC"
validator    -> refData "Resolves instruments against" "gRPC"

// --- OMS to EMS order flow, and fills back ---
lifecycle  -> algoEngine "Stages parent orders to" "FIX 4.4"
fixGateway -> lifecycle "Reports fills and order status to" "FIX 4.4"

// --- Execution internals ---
execUi     -> algoEngine "Controls algo parameters in"
algoEngine -> sor "Slices child orders through"
sor        -> fixGateway "Routes child orders via"
fixGateway -> execStore "Journals routes and executions to"
algoEngine -> mdBus "Consumes real-time prices from"
sor        -> mdBus "Consumes venue liquidity signals from"
tca        -> execStore "Analyses executions from"
tca        -> tickStore "Benchmarks against market history in"

// --- Market data flow ---
feedHandler -> vendorData "Subscribes to real-time feeds from"
feedHandler -> mdBus "Publishes normalised ticks to"
feedHandler -> tickStore "Captures history into"
refData     -> vendorData "Sources security master data from"

// --- Risk & PnL flow ---
riskEngine -> mdBus "Consumes live prices from"
riskEngine -> positionSvc "Streams position updates from"
riskEngine -> riskStore "Writes exposures and Greeks to"
varSvc     -> tickStore "Loads historical scenarios from"
varSvc     -> riskStore "Stores VaR and stress results in"
pnlSvc     -> positionSvc "Sources positions and cash from"
pnlSvc     -> riskStore "Writes P&L attribution to"
riskUi     -> riskStore "Reads exposures, VaR and P&L from"

// --- External connectivity ---
fixGateway       -> venues "Sends child orders to / receives executions from" "FIX 4.4"
allocEngine      -> primeBroker "Sends allocations for clearing to" "FIX allocations"
positionSvc      -> primeBroker "Reconciles financing and borrow with" "SFTP"
positionSvc      -> custodian "Confirms settlement status with" "SWIFT"
pnlSvc           -> fundAdmin "Reconciles NAV and P&L with" "SFTP"
complianceEngine -> regGateway "Submits transaction reports to" "HTTPS"
