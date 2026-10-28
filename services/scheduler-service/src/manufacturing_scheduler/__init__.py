"""Scheduling snapshot consumer and RecoveryPlan proposal contract (WP-SCH-002).

An offline library: it consumes the published Core/Twin snapshot and decodes,
validates and serializes RecoveryPlan proposals. It has no server, store, broker or
Core access, no solver and no validator, and it activates, approves and executes
nothing.
"""
