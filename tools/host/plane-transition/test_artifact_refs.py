"""CTRL-HOST-003: sentence punctuation must not become a GitHub file path.

Offline regression of PR #76's exact failing evidence read. No credentials,
network, lifecycle evaluator or Plane mutation are used.
"""

import unittest
from unittest.mock import patch

from test_transition import HEAD, fixture, t

PATH = "evidence/WP-EVT-002/WORLD-SCOPE-SLICE.md"
REF = "repo:" + PATH


class ArtifactReferenceTests(unittest.TestCase):
    def test_exact_pr_76_evidence_sentence_reads_the_actual_file(self):
        wp, policy, _, gh, _ = fixture(source="IN_REVIEW", target="MERGE_READY")
        gh.pr_data["body"] = gh.pr_data["body"].replace(
            "[Actual run](evidence/test.json)", REF + ". Historical source SHAs follow."
        )
        client = object.__new__(t.GitHub)

        def read(route):
            if route != f"{t.REPO}/contents/{PATH}?ref={HEAD}":
                raise t.Denied("GITHUB_READ_UNAVAILABLE")  # old path returns HTTP 404
            return {"type": "file", "size": 100}

        with (
            patch.object(client, "_get", side_effect=read) as request,
            patch.object(gh, "artifact", side_effect=client.artifact),
        ):
            t.pr_governance(gh, gh.pr_data, wp, policy["contexts"][wp], policy)
        request.assert_called_once_with(f"{t.REPO}/contents/{PATH}?ref={HEAD}")

    def test_bare_sentence_end_and_whitespace_are_not_path_characters(self):
        for suffix in (".", ". Next sentence", ".\nNext line", "... Next sentence"):
            with self.subTest(suffix=suffix):
                self.assertEqual(t.artifact_refs(REF + suffix), [REF])

    def test_quoted_paths_are_literal_even_when_they_end_in_a_dot(self):
        for ticks in ("`", "``", "```"):
            for code in (REF + ".", "Exact file: " + REF + ". More code"):
                with self.subTest(ticks=ticks, code=code):
                    self.assertEqual(t.artifact_refs(ticks + code + ticks), [REF + "."])

    def test_markdown_destinations_are_literal(self):
        self.assertEqual(t.artifact_refs(f"[proof]({PATH}.)"), [REF + "."])
        self.assertEqual(t.artifact_refs(f"[proof]({REF}.)"), [REF + "."])

    def test_internal_dots_ordering_deduplication_and_artifact_ids_are_preserved(self):
        self.assertEqual(
            t.artifact_refs(f"{REF}. {REF} artifact:123. repo:evidence/run.v1.json."),
            ["artifact:123", REF, "repo:evidence/run.v1.json"],
        )

    def test_genuinely_missing_file_still_fails_without_an_alternate_read(self):
        client = object.__new__(t.GitHub)
        with (
            patch.object(
                client, "_get", side_effect=t.Denied("GITHUB_READ_UNAVAILABLE")
            ) as request,
            self.assertRaises(t.Denied) as denied,
        ):
            client.artifact(
                t.artifact_refs("repo:evidence/missing.md. Absent.")[0], HEAD
            )
        self.assertEqual(denied.exception.code, "GITHUB_READ_UNAVAILABLE")
        request.assert_called_once_with(
            f"{t.REPO}/contents/evidence/missing.md?ref={HEAD}"
        )

    def test_explicit_literal_dot_is_not_silently_replaced_by_an_existing_file(self):
        client = object.__new__(t.GitHub)
        with (
            patch.object(
                client, "_get", side_effect=t.Denied("GITHUB_READ_UNAVAILABLE")
            ) as request,
            self.assertRaises(t.Denied),
        ):
            client.artifact(t.artifact_refs(f"`{REF}.`")[0], HEAD)
        request.assert_called_once_with(f"{t.REPO}/contents/{PATH}.?ref={HEAD}")

    def test_traversal_invalid_sha_and_non_file_evidence_still_fail_closed(self):
        client = object.__new__(t.GitHub)
        for reference, sha in (("repo:../missing.md.", HEAD), (REF + ".", "not-a-sha")):
            with (
                self.subTest(reference=reference),
                patch.object(client, "_get") as request,
            ):
                with self.assertRaises(t.Denied) as denied:
                    client.artifact(t.artifact_refs(reference)[0], sha)
                self.assertEqual(denied.exception.code, "INVALID_ARTIFACT_PATH")
                request.assert_not_called()
        for value in ({"type": "dir", "size": 100}, {"type": "file", "size": 0}):
            with (
                self.subTest(value=value),
                patch.object(client, "_get", return_value=value),
            ):
                with self.assertRaises(t.Denied) as denied:
                    client.artifact(t.artifact_refs(REF + ".")[0], HEAD)
                self.assertEqual(denied.exception.code, "ARTIFACT_NOT_A_FILE")


if __name__ == "__main__":
    unittest.main()
