def pytest_configure(config):  # type: ignore[no-untyped-def]
    config.addinivalue_line(
        "markers", "integration: needs the REAL Collector and OpenObserve (stack.sh up)"
    )
