# 2. Colocate the execution hot path in Equinix NY4

Date: 2026-05-18

## Status

Accepted

## Context

Execution quality is dominated by tick-to-trade latency. Cloud regions
add hundreds of microseconds of jitter and provide no deterministic
network path to venue matching engines.

## Decision

Run the algo engine, smart order router, FIX gateway and feed handlers
on bare-metal servers in Equinix NY4 with kernel-bypass NICs and direct
venue cross-connects. Everything without a microsecond budget stays in
AWS.

## Consequences

Deterministic single-digit-microsecond wire-to-wire latency; higher
operational burden (hardware lifecycle, remote hands) and a Direct
Connect dependency for the colo-to-cloud data path.
