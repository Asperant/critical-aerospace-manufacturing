"""Offline fixtures only: bounded, complete PR file pagination in the shared adapter."""

import importlib.util
import re
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "transition_for_pr_files", HERE / "transition.py"
)
assert spec is not None and spec.loader is not None
t: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
qs = importlib.util.spec_from_file_location(
    "queue_for_pr_files", HERE.parent / "plane-queue" / "queue.py"
)
assert qs is not None and qs.loader is not None
t.q = importlib.util.module_from_spec(qs)
qs.loader.exec_module(t.q)

NUMBER = 52
ROUTE_PREFIX = f"repos/Asperant/critical-aerospace-manufacturing/pulls/{NUMBER}"


def rows_for(total):
    return [{"filename": f"dir/file{i}.py", "status": "added"} for i in range(total)]


class Adapter:
    """A GitHub adapter whose only network call is a recording stub."""

    def __init__(self, total, rows=None, changed=None):
        self.rows = rows_for(total) if rows is None else rows
        self.changed = total if changed is None else changed
        self.calls = []
        self.after_first_page: Any = None
        self.raw_page: Any = None  # when set, returned verbatim for every file page
        gh = object.__new__(t.GitHub)
        gh.cache = {}
        gh._get = self.get
        self.gh = gh
        self.pr = {"number": NUMBER, "changed_files": total}

    def get(self, route):
        self.calls.append(route)
        if route == ROUTE_PREFIX:
            return {"number": NUMBER, "changed_files": self.changed}
        match = re.fullmatch(
            re.escape(ROUTE_PREFIX) + r"/files\?per_page=100&page=([0-9]+)", route
        )
        assert match, route
        page = int(match[1])
        if self.after_first_page and page == 1:
            self.after_first_page()
        if self.raw_page is not None:
            return self.raw_page
        return self.rows[(page - 1) * 100 : page * 100]

    def files(self):
        return self.gh.files(self.pr)


class PaginationTests(unittest.TestCase):
    def test_boundary_counts_return_the_complete_inventory(self):
        for total in (0, 1, 99, 100, 101, 131, 200, 201, 999, 1000):
            with self.subTest(total=total):
                adapter = Adapter(total)
                rows = adapter.files()
                self.assertEqual(len(rows), total)
                self.assertEqual(
                    [x["filename"] for x in rows],
                    [x["filename"] for x in rows_for(total)],
                )

    def test_the_ceiling_is_ten_pages_and_larger_is_rejected_before_any_page_read(self):
        adapter = Adapter(1000)
        adapter.files()
        self.assertEqual(len([c for c in adapter.calls if "/files?" in c]), 10)
        too_big = Adapter(1001, rows=rows_for(1001))
        with self.assertRaises(t.Denied) as caught:
            too_big.files()
        self.assertEqual(caught.exception.code, "PR_FILE_SCOPE_EXCEEDS_CEILING")
        self.assertEqual([c for c in too_big.calls if "/files?" in c], [])

    def test_short_missing_or_extra_pages_are_incomplete(self):
        cases = {
            "short middle page": (200, rows_for(200)[:99] + rows_for(200)[100:]),
            "missing last page": (200, rows_for(200)[:100]),
            "short last page": (131, rows_for(131)[:130]),
            "extra rows beyond count": (100, rows_for(101)),
            "no rows": (3, []),
        }
        for name, (total, rows) in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(t.Denied) as caught:
                    Adapter(total, rows=rows).files()
                self.assertEqual(caught.exception.code, "INCOMPLETE_PR_FILE_SCOPE")

    def test_repeated_pages_and_duplicate_paths_are_rejected(self):
        page = rows_for(100)
        with self.assertRaises(t.Denied) as caught:
            Adapter(200, rows=page + page).files()
        self.assertEqual(caught.exception.code, "DUPLICATE_PR_FILE_PATH")
        twice = [{"filename": "a.py", "status": "added"}] * 2
        with self.assertRaises(t.Denied) as caught:
            Adapter(2, rows=twice).files()
        self.assertEqual(caught.exception.code, "DUPLICATE_PR_FILE_PATH")

    def test_a_changing_inventory_is_rejected(self):
        adapter = Adapter(131)

        def change():
            adapter.changed = 132

        adapter.after_first_page = change
        with self.assertRaises(t.Denied) as caught:
            adapter.files()
        self.assertEqual(caught.exception.code, "PR_FILE_SCOPE_CHANGED")


class ScopePathTests(unittest.TestCase):
    def test_unsafe_runtime_and_secret_paths_are_rejected(self):
        for path in (
            "/etc/passwd",
            "a/../b.py",
            "services/x/.env",
            "tools/plane.env",
            "a/.venv/lib.py",
            "a/__pycache__/m.pyc",
            "pkg.egg-info/PKG-INFO",
            "project_control/local/secret.txt",
            "keys/id_rsa",
        ):
            with self.subTest(path=path), self.assertRaises(t.Denied):
                t.pr_scope_paths([{"filename": path, "status": "added"}])


if __name__ == "__main__":
    unittest.main()
