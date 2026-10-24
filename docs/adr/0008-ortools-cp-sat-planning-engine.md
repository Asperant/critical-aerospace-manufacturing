# ADR-0008: OR-Tools CP-SAT as the planning engine

- **ADR-ID**: ADR-0008
- **Title**: OR-Tools CP-SAT as the planning engine
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Batu, Yavuz Gümüş
- **DecisionLevel**: ADR-L2
- **AffectedCapabilities**: Scheduler optimization engine (ARCH-SCH-ENGINE)
- **AffectedRequirements**: FR-SCH-009 (DECIDED_BY edge in the RTM; a decision link, never verification)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: Single-CP-SAT-formulation scope debt recorded in the specification (Item 71); no debt ID cited here
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Items 19 and 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

Item 19 named CP-SAT only as the strong candidate without locking the technology. Item 61 settles the selection of the primary optimization engine for scheduling.

## Decision Drivers

Machine eligibility, precedence, maintenance windows, scheduling constraints, and multi-objective and rolling-horizon scheduling.

## Constraints/Assumptions

- Scheduler output is a plan, never a command; the Scheduler does not mutate manufacturing state.
- Custom dispatch heuristics (FIFO, EDD, CR, SPT, SRPT) remain the selected scheduling baselines.
- Solve inputs and outputs are logged for experiment evidence; solve behavior is bounded.

## Considered Options

- Google OR-Tools CP-SAT: **selected** as the primary optimization engine.
- Commercial solvers (Gurobi, CPLEX): not mandatory.
- RL and metaheuristic approaches: not mandatory; if added they must be benchmarked against every baseline, since an "AI scheduling" label alone is not justification.

## Decision

Google OR-Tools' CP-SAT solver is the primary optimization engine for scheduling.

## Rationale

Item 61 treats the selection as settled; CP-SAT covers the constraint types the Scheduler needs, with dispatch heuristics as baselines.

## Positive Consequences

Stateless solver invocation with no persistent solver state to rebuild; capability degrades to dispatch heuristics rather than to zero if the solver is lost.

## Negative Consequences

The specification records that the Scheduler has a single CP-SAT formulation rather than several research formulations (Technical/Scope Debt, Item 71), which may become the final design.

## Risks

Loss of the solver degrades scheduling to dispatch heuristics. An unbounded solve or a missing independent validator would be invalid forms of scheduler debt.

## Operational Impact

Owner: Batu. The solver is invoked statelessly and its inputs and outputs are logged as experiment evidence.

## Security/Authority Impact

Low. The solver produces a plan, not a command; the independent `ScheduleValidator` is separate.

## Research/Evidence Impact

Solve inputs and outputs are logged as experiment evidence. Any RL or metaheuristic addition needs benchmarking against all baselines.

## Migration/Rollback

Reversibility class: `REVERSIBLE` (assigned by this record's author, because the solver is stateless and heuristic baselines exist). A change of planning engine is a mandatory ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Validation evidence is attached when the CP-SAT formulation is validated against the baselines.

## Revisit Triggers

If a benchmarked alternative beats the baselines and CP-SAT on the defined objectives, or if the single formulation proves insufficient (Item 71 debt).

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Scheduler Architecture; Technical Debt Register (Item 71); The Backfill ADR Set.
- [ADR index](README.md)
