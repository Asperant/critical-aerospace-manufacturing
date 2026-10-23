"""operations-bff runtime foundation: session, CSRF and ActorContext primitives.

Framework neutral by design: FastAPI is a transport adapter added later, and
nothing here contacts an identity provider, a broker or a database.
"""
