# Demo architecture view

The presenter can explain this in under 30 seconds:

```text
                         +------------------+
                         | Keycloak         |
                         | demo.operator OIDC|
                         +---------+--------+
                                   |
+----------------+        +-------v-------+        +------------------+
| Browser / UI   +--------> BFF            +-------> Twin read model |
| localhost:29090|        | session + read |        | FRESH projection |
+----------------+        +----------------+        +--------+---------+
                                                            ^
                                                            |
+----------------+   transaction   +----------------+   NATS/JetStream
| Core command   +----------------->| PostgreSQL    +----------+
| localhost:28091|                  | state+outbox  |          |
+----------------+                  +----------------+   +------v------+
                                                        | Twin consumer|
                                                        | twin-primary  |
                                                        +--------------+
```

Core is authoritative. The outbox and relay carry committed events. Twin is a
rebuildable projection; BFF and UI only read it. The diagram describes this
demo slice and does not imply physical equipment control or production
acceptance.
