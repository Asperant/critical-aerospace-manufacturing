from __future__ import annotations

import fast_scope_tests


def test_projectctl_gate_change_selects_its_own_suite(monkeypatch):
    selected = []
    monkeypatch.setattr(
        fast_scope_tests,
        "changed_paths",
        lambda: [
            "tools/projectctl/src/projectctl/post_merge_evidence.py",
            "tools/projectctl/tests/test_gates.py",
            "tools/projectctl/README.md",
        ],
    )
    monkeypatch.setattr(
        fast_scope_tests,
        "run",
        lambda label, command: selected.append((label, command)),
    )

    assert fast_scope_tests.main() == 0
    assert len(selected) == 1
    label, command = selected[0]
    assert label == "projectctl-changed-scope"
    assert command[-2:] == ["tools/projectctl/tests/test_gates.py", "-q"]
    assert "tools/projectctl/tests/test_cli.py" not in command
    assert "tools/projectctl/tests/test_project.py" not in command


def test_changed_projectctl_test_runs_without_unrelated_default_suites(monkeypatch):
    selected = []
    monkeypatch.setattr(
        fast_scope_tests,
        "changed_paths",
        lambda: ["tools/projectctl/tests/test_dependencies.py"],
    )
    monkeypatch.setattr(
        fast_scope_tests,
        "run",
        lambda label, command: selected.append((label, command)),
    )

    assert fast_scope_tests.main() == 0
    assert len(selected) == 1
    assert selected[0][1][-2:] == [
        "tools/projectctl/tests/test_dependencies.py",
        "-q",
    ]
