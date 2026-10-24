# ADR-0013: A custom, explicit AI orchestrator rather than a heavy agent framework

- **ADR-ID**: ADR-0013
- **Title**: A custom, explicit AI orchestrator rather than a heavy agent framework
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: None named in the specification
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: AI orchestrator (ARCH-AI-ORCH); structured RCA reasoning
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge uses the placeholder `backfill-13`)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 28 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

Item 28 fixes the architectural pattern for the AI orchestrator (a deterministic, runtime-controlled state machine) and names no orchestration library; it lists the exact framework as an open question. Item 61 selects a custom explicit orchestrator and rejects named frameworks as the core.

## Decision Drivers

- Deterministic state control: the LLM cannot skip mandatory transitions.
- A hard per-task tool allowlist with no unrestricted tool discovery.
- Authority containment: the prompt is not a security boundary.
- Auditability: Investigation, AgentRun, Evidence, Hypothesis, RootCauseAssessment and Recommendation persist as structured, versioned state.

## Constraints/Assumptions

- A single orchestrator is the core topology; a multi-agent design is a benchmarked research extension only.
- "Single orchestrator" is not "single prompt": the orchestrator runs a sequence of logical phases, none of which is an autonomous agent.
- The exact orchestration runtime form (hand-rolled state machine, internal DSL, or a thin layer over a workflow engine) remains an open decision and is not decided here.

## Considered Options

- Custom explicit orchestrator in Python: **selected**.
- LangChain: rejected as the core framework.
- LangGraph: rejected as the core framework.
- Unbounded ReAct loop: rejected (weak control over termination, authority, cost and reliability).
- Multi-agent swarm: not the default; "multi-agent is more modern" is not sufficient justification.

## Decision

The AI orchestrator is a custom, explicit, deterministic Python orchestrator that owns phases, state, tools, budgets, authority, retries and outputs, rather than a general-purpose agent framework.

## Rationale

Generic agent-loop frameworks are built around flexible, model-driven control flow, which is the opposite of the hard requirements for deterministic state, tool admission control by the runtime, and authority enforced outside the model.

## Positive Consequences

Termination, authority, cost and tool use are controlled by the runtime, and structured intelligence artifacts are auditable first-class state.

## Negative Consequences

The specification does not enumerate negative consequences. The record author notes that the project owns the orchestrator implementation; this is an observation, not a specification statement.

## Risks

The orchestrator's implementation form is still open, so the behavioral contract (bounded, deterministic, typed-tool-only) is the binding part of this decision.

## Operational Impact

The orchestrator runs inside the AI intelligence service, alongside long-running investigation workers for multi-step investigations.

## Security/Authority Impact

High relevance: operational authority must not rely on system-prompt instructions. It is enforced by tool allowlists, receiver-side authorization and typed backend contracts, so the AI never directly mutates manufacturing state.

## Research/Evidence Impact

Any multi-agent extension must show measurable improvement in RCA accuracy, latency, cost, tool-use correctness or maintainability.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author, because tools, state schemas and audit artifacts are built against the orchestrator). An AI authority change is a mandatory ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Validation evidence is attached when the orchestrator state machine, tool allowlist and authority negative tests exist.

## Revisit Triggers

If a benchmarked framework can satisfy the deterministic-state, allowlist and authority constraints with measurable benefit, or if the exact runtime form is decided by a later ADR.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; AI Intelligence Service Architecture (Single Orchestrator, rejected alternatives); The Backfill ADR Set.
- [ADR index](README.md)
