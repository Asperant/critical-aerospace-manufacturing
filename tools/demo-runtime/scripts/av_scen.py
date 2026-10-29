#!/usr/bin/env python3
"""Executable wrapper for the real WP-CORE-008 AV-SCEN slices."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/demo-runtime/src"))

from cap_demo_runtime.av_scenarios import main  # noqa: E402

raise SystemExit(main())
