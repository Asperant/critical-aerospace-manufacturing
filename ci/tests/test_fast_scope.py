"""Static safety checks for the bounded PR scope selector."""

from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "fast_scope_tests.py"


def test_fast_scope_has_bounded_timeout_and_no_full_projectctl_suite() -> None:
    text = SCRIPT.read_text()
    assert "TIMEOUT = 90" in text
    assert "tools/projectctl/tests/test_execution_queue.py" in text
    assert "tools/projectctl/tests -q" not in text


def test_fast_scope_requires_an_explicit_base() -> None:
    text = SCRIPT.read_text()
    assert "FAST_GATE_BASE" in text
    assert "if not base" in text
