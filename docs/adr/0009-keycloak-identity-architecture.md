# ADR-0009: Keycloak as the identity architecture

- **ADR-ID**: ADR-0009
- **Title**: Keycloak as the identity architecture
- **Status**: ACCEPTED
- **Date**: 2026-10-24
- **DecisionOwner**: Asrın Dündar
- **Reviewers**: Yavuz Gümüş
- **DecisionLevel**: ADR-L3
- **AffectedCapabilities**: Identity provider (ARCH-SEC-IDP); authentication for operators, HITL approvals and service identity
- **AffectedRequirements**: None linked yet (no DECIDED_BY edge uses the placeholder `backfill-09`)
- **AffectedRisks**: None linked yet
- **AffectedDebt**: None
- **Supersedes**: None
- **SupersededBy**: None
- **ValidationState**: PENDING

> Backfill record. This ADR documents a decision that was **already made**
> (Master Specification Item 61) and already incorporated into the
> architecture specification. It does not propose or change anything. The date is
> the date this record was written, not the date of the decision.

## Context

The platform needs a central identity provider for user authentication and service identity in every non-toy environment. Item 61 names the product.

## Decision Drivers

A self-hosted identity provider offering OIDC/OAuth2 for user authentication and service identity, with authorization kept in the backend.

## Constraints/Assumptions

- Keycloak authentication does not replace backend authorization (`TECH-INV-18`). Keycloak claims are input; the platform's own policy engine makes the authoritative decision.
- "Keycloak Admin is not Manufacturing Approver": administrative rights confer no approval authority.
- OIDC abstraction and authorization logic stay separate from Keycloak internals.

## Considered Options

Keycloak is the selected product. The specification does not enumerate rejected identity-provider alternatives for this decision.

## Decision

Keycloak, self-hosted, is the identity provider (OIDC/OAuth2) for user authentication and service identity.

## Rationale

Item 61 selects Keycloak as the product satisfying the identity requirements, with authorization remaining in the platform policy engine.

## Positive Consequences

Authentication is centralized, and keeping the OIDC abstraction and authorization logic separate limits the exit cost.

## Negative Consequences

The specification does not enumerate negative consequences. See Risks for the availability dependency.

## Risks

Loss of Keycloak blocks authentication for HITL approvals and operator access, which halts the governed authority path.

## Operational Impact

Semantic owner of the authorization architecture: Asrın. Runtime owner: Yavuz. The identity store is stateful and durable, and is part of the platform security posture.

## Security/Authority Impact

High: it gatekeeps human approval identity. The browser is reached only through the Edge/BFF zone, which performs the Keycloak-class OIDC flow and holds no business authority.

## Research/Evidence Impact

None stated in the specification for this decision.

## Migration/Rollback

Reversibility class: `COSTLY_TO_REVERSE` (assigned by this record's author; the specification says the OIDC abstraction limits the exit cost, but identity underlies all approvals). A security or trust-boundary change is a mandatory ADR trigger. A reversal needs a new superseding ADR and follows prepare -> compatibility/migrate -> cutover -> verify -> remove old path.

## Validation Plan

`ValidationState` stays `PENDING`. Evidence level of the decision itself: `E1` (documentation). Validation evidence is attached when real OIDC authentication, service identity and backend authorization negative tests exist.

## Revisit Triggers

If backend authorization can no longer stay independent of Keycloak claims, or if the Item 61 promotion and exit policy for the identity provider is triggered.

## References

- [System Architecture Specification](../02_System_Architecture_Specification.md):
  Technology Baseline; Security Architecture; `TECH-INV-18`; The Backfill ADR Set.
- [ADR index](README.md)
