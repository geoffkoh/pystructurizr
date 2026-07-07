# 3. Use kdb+ for tick storage

Date: 2026-06-02

## Status

Proposed

## Context

Quant research and TCA need years of full-depth tick history with
fast as-of joins; PostgreSQL and Timescale struggle at this volume
and query shape.

## Decision

Store normalised tick and bar data in kdb+, fronted by the market
data platform's tick store container.

## Consequences

Excellent columnar performance and mature as-of joins, at the cost of
q expertise and per-core licensing; revisit if open alternatives
(e.g. QuestDB, ClickHouse) close the gap for our workloads.
