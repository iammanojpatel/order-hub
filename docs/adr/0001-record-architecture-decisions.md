# 1. Record architecture decisions

- Status: Accepted
- Date: 2026-10-10

## Context
Decisions that are expensive to reverse need a durable, reviewable record of why they were made.

## Decision
We use Architecture Decision Records (MADR format) in `docs/adr/`, numbered sequentially. Claude Code's `/adr` skill and the `solution-architect` agent create them. Superseded ADRs are kept and marked `Superseded by NNNN`.

## Consequences
New engineers and AI agents can see the reasoning behind each decision, and changes to decisions are explicit and reviewed in PRs.
