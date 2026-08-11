"""
Shared helpers for the Phase 3 cost scripts.

resolve_output_dir()
    Windows Defender's "Controlled Folder Access" (or a similar
    endpoint policy) has been blocking real file writes inside this
    project's folder tree even when a trivial probe write succeeds
    and icacls shows full control (see evaluation/evaluate.py for
    the full writeup). This helper does a REAL write test (not just
    a touch) and falls back to the system temp directory if the
    preferred location isn't actually writable. Every Phase 3 script
    imports this so they all agree on where their files land.

find_latest_file()
    Searches a list of candidate directories for files matching a
    glob pattern and returns the most recently modified match. Used
    by savings_analysis.py to locate Phase 1's quality_gate_*.csv
    without hardcoding a single path (since evaluate.py's own output
    location can itself fall back to temp).
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Iterable, Optional


def _real_write_test(candidate: Path) -> None:
    """Write something close to a real CSV (not a 1-byte touch),
    flush, and fsync before deleting — trivial writes have been seen
    to slip through Controlled Folder Access even when real writes
    from library code (e.g. pandas.to_csv) are blocked.
    """
    probe = candidate / f".write_test_{uuid.uuid4().hex}.tmp"
    with open(probe, "w", encoding="utf-8", newline="") as f:
        f.write("col_a,col_b\n1,2\n" * 50)
        f.flush()
        os.fsync(f.fileno())
    probe.unlink()


def resolve_output_dir(preferred: Path, subfolder: str = "") -> Path:
    """Return a directory that genuinely accepts real file writes.

    Tries system temp FIRST (outside the project tree, so it isn't
    affected by per-folder policies scoped to the project directory),
    then `preferred`, then C:\\Temp as a last resort on Windows.
    """
    base_temp = Path(tempfile.gettempdir()) / "afyaplus_outputs"
    temp_candidate = (base_temp / subfolder) if subfolder else base_temp

    candidates = [temp_candidate, preferred]

    if os.name == "nt":
        c_temp = Path("C:/Temp/afyaplus_outputs")
        candidates.append((c_temp / subfolder) if subfolder else c_temp)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _real_write_test(candidate)

            if candidate != preferred:
                print(
                    f"⚠️  NOTE: Writing output to:\n    {candidate}\n"
                    f"   instead of the project folder:\n    {preferred}\n"
                    f"   (Controlled Folder Access workaround — see "
                    f"evaluation/evaluate.py's bottom comment for the "
                    f"permanent fix.)\n"
                )

            return candidate

        except (PermissionError, OSError) as e:
            print(f"Cannot write to {candidate}: {e}")
            continue

    raise RuntimeError(
        "No writable output directory found. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


def find_latest_file(
    dirs: Iterable[Path], filename_glob: str
) -> Optional[Path]:
    """Search several candidate directories for files matching
    `filename_glob` and return the most recently modified match
    across all of them, or None if nothing was found anywhere.
    """
    matches = []
    for d in dirs:
        d = Path(d)
        if d.exists():
            matches.extend(d.glob(filename_glob))

    if not matches:
        return None

    return max(matches, key=lambda p: p.stat().st_mtime)
