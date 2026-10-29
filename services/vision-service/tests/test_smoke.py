"""TEST-VIS-CPUSMOKE: CPU-only smoke path behind `mfgctl smoke vision` (WP-VIS-008)."""

import json
from pathlib import Path

import numpy as np
import pytest
from conftest import REPO
from vision_service import decode_png, smoke


def test_smoke_passes_on_cpu_and_reports_its_limits() -> None:
    report = smoke.run(count=4, size=64, root=REPO)
    assert report["result"] == "PASS"
    assert report["functional_ok"] is True
    assert report["accelerator_used"] is False
    assert report["sample"] == {
        "version": "vision-smoke-synthetic/1",
        "images": 4,
        "size_px": [64, 64],
        "provenance": "SYNTHETIC",
    }
    assert report["max_s_per_image"] <= smoke.THRESHOLD_S
    assert "not NFR-PERF-009 acceptance" in report["limitation"]
    assert report["host"]["hardware_profile"] in {
        "PRIMARY_SHARED_HOST (01 Final Human Reconciliation)",
        "UNRECOGNIZED_HOST",
    }
    assert report["host"]["logical_cpus"]
    assert [item["outcome"] for item in report["images"]] == [
        "DEFECT_CANDIDATES",
        "NO_DEFECT_CANDIDATES",
        "DEFECT_CANDIDATES",
        "NO_DEFECT_CANDIDATES",
    ]


def test_sample_is_deterministic_and_decodable() -> None:
    first, second = smoke.sample(3, 32), smoke.sample(3, 32)
    assert [image.png for image in first] == [image.png for image in second]
    decoded = decode_png(first[0].png)
    assert decoded.shape == (32, 32, 1)
    assert decoded.dtype == np.uint8


def test_threshold_breach_fails_the_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smoke, "THRESHOLD_S", 0.0)
    report = smoke.run(count=2, size=32, root=REPO)
    assert report["result"] == "FAIL"


def test_functional_mismatch_fails_the_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    original = smoke.sample

    def inverted(count: int, size: int) -> list[smoke.SampleImage]:
        return [
            smoke.SampleImage(image.name, image.png, not image.expects_candidates)
            for image in original(count, size)
        ]

    monkeypatch.setattr(smoke, "sample", inverted)
    report = smoke.run(count=2, size=32, root=REPO)
    assert report["functional_ok"] is False
    assert report["result"] == "FAIL"


def test_smoke_loads_explicit_cpu_package_and_rejects_invalid_manifest(
    tmp_path: Path,
) -> None:
    package = REPO / smoke.PACKAGE_RELATIVE
    loaded = smoke.load_package(package)
    assert loaded.package_id == "vision-baseline-local-deviation"
    assert loaded.promoted is False
    invalid = tmp_path / "package.json"
    invalid.write_text("{}", encoding="utf-8")
    with pytest.raises(smoke.SmokeInputError):
        smoke.load_package(invalid)


def test_sample_manifest_requires_explicit_labels_and_safe_paths(tmp_path: Path) -> None:
    image = smoke.sample(1, 32)[0]
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(image.png)
    manifest = tmp_path / "sample.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "vision.smoke-sample/v1",
                "provenance": "ACCEPTED",
                "images": [
                    {
                        "name": "accepted-1",
                        "path": "sample.png",
                        "expects_candidates": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert smoke.load_sample_manifest(manifest)[0].name == "accepted-1"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            '"sample.png"', '"../sample.png"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(smoke.SmokeInputError):
        smoke.load_sample_manifest(manifest)


def test_cli_exit_codes_and_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO)
    assert smoke.main(["--images", "2", "--size", "32", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["result"] == "PASS"
    monkeypatch.setattr(smoke, "THRESHOLD_S", 0.0)
    assert smoke.main(["--images", "1", "--size", "32"]) == 1
    with pytest.raises(SystemExit):
        smoke.main(["--size", "8"])


def test_registered_mfgctl_capability_points_at_the_smoke_script() -> None:
    registry = json.loads((REPO / "infra/mfgctl/capabilities.json").read_text("utf-8"))
    (vision,) = (c for c in registry["capabilities"] if c["name"] == "vision")
    assert vision["owner"] == "Selman"
    assert vision["smoke"] == ["services/vision-service/smoke.sh"]
    script = Path(REPO / vision["smoke"][0])
    assert script.is_file() and script.stat().st_mode & 0o100
    assert "nvidia" not in script.read_text("utf-8").lower()
