import ast
from pathlib import Path

ROOT = Path(__file__).parent


def test_launcher_has_fixed_two_argument_profile_wp_surface():
    text = (ROOT / "cap-plane-slot-release-diagnostic").read_text()
    assert '"$#" -ne 2' in text
    assert (
        'exec /usr/bin/sudo -n /usr/bin/python3 -I /usr/local/libexec/cap-plane-slot-release-diagnostic.py "$1" "$2"'
        in text
    )
    assert "eval" not in text and "sh -c" not in text


def test_diagnostic_source_has_no_mutation_calls_or_secret_output():
    tree = ast.parse((ROOT / "slot_release_diagnostic.py").read_text())
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert not {"patch", "append_audit", "unlink", "replace", "write_text"} & set(calls)
    text = (ROOT / "slot_release_diagnostic.py").read_text()
    assert "print(key" not in text


def test_installer_uses_exact_profile_wp_sudoers_and_deploys_diagnostic():
    text = (ROOT / "install_auto_next.py").read_text()
    assert "DIAGNOSTIC_SUDOERS" in text
    assert "cap-plane-slot-release-diagnostic.py {profile} {wp}" in text
    assert "cap-plane-slot-release-diagnostic.py {profile} WP-*" not in text
    assert "slot_release_diagnostic.py" in text
