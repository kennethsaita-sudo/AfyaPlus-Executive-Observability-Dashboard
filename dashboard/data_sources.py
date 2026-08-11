"""
Locates the latest CSV/JSON outputs produced by the other three
phases (evaluation, cost, drift) so the dashboard can render real
data regardless of which fallback location a given file ended up in
— see evaluation/evaluate.py's notes on the Kaspersky Endpoint
Security / Controlled Folder Access workaround used throughout this
project. C:\\Temp\\afyaplus_outputs is the primary location; the
project's own outputs/ folders are checked too in case that gets
fixed later.
"""

from pathlib import Path
from typing import List, Optional

DASHBOARD_DIR = Path(__file__).parent
PROJECT_ROOT = DASHBOARD_DIR.parent

C_TEMP_ROOT = Path("C:/Temp/afyaplus_outputs")


def _candidate_dirs(phase_subfolder: str = "") -> List[Path]:
    dirs = [
        PROJECT_ROOT / "evaluation" / "outputs",
        PROJECT_ROOT / "evaluation" / "_fallback_outputs",
        PROJECT_ROOT / "cost" / "outputs",
        PROJECT_ROOT / "drift" / "outputs",
        C_TEMP_ROOT,
        Path("C:/Temp/afyaplus_outputs_fallback"),
    ]
    if phase_subfolder:
        dirs.insert(0, C_TEMP_ROOT / phase_subfolder)
    return dirs


def find_latest(filename_glob: str, phase_subfolder: str = "") -> Optional[Path]:
    """Return the most recently modified file matching
    `filename_glob` across every folder a given phase's script might
    have written to, or None if nothing matches anywhere.
    """
    matches = []
    for d in _candidate_dirs(phase_subfolder):
        if d.exists():
            matches.extend(d.glob(filename_glob))

    if not matches:
        return None

    return max(matches, key=lambda p: p.stat().st_mtime)
