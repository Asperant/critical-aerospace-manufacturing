def pytest_configure(config):  # type: ignore[no-untyped-def]
    config.addinivalue_line(
        "markers",
        "integration: needs Docker; the REAL runtime tests need stack.sh up infra",
    )
