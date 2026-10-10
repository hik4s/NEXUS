# ADR 0001 — Start as a modular monolith

## Decision

Build NEXUS as a modular monolith initially.

## Why

A monolith lets us learn and validate domain boundaries without the operational overhead of distributed systems. Redis, workers and separate services can be introduced when concrete requirements appear.
