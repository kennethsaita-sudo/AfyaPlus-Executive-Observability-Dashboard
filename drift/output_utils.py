"""
Shared helpers for the Phase 2 drift scripts — identical pattern to
cost/output_utils.py, duplicated here since each phase folder runs
as its own standalone script (no shared package structure).

resolve_output_dir()
    C:\\Temp was confirmed reliable on this machine after
    troubleshooting; %LOCALAPPDATA%\\Temp (Python's default temp
    dir) and the project folder itself were both intermittently
    blocked by Kaspersky Endpoint Security. C:\\Temp is tried first.

write_dataframe_csv()
    Avoids pandas' internal `to_csv(path)` file-opening code path,
    which was also observed to be blocked in places where a plain
    `open()` call succeeded. Builds the CSV as a string in memory
    first, then writes it with a bare `open()` call instead.
"""

import os
import uuid
from pathlib import Path
from typing import Iterable, Optional


def _real_write_test(candidate: Path) -> None:
    probe = candidate / f".write_test_{uuid.uuid4().hex}.tmp"
    with open(probe, "w", encoding="utf-8", newline="") as f:
        f.write("col_a,col_b\n1,2\n" * 50)
        f.flush()
        os.fsync(f.fileno())
    probe.unlink()


def resolve_output_dir(preferred: Path, subfolder: str = "") -> Path:
    """Return a directory that genuinely accepts real file writes.

    C:\\Temp is tried FIRST on Windows (confirmed reliable on this
    machine). `preferred` (the project's own outputs folder) is
    tried second, in case Kaspersky/Controlled Folder Access gets
    reconfigured later.
    """
    candidates = []

    if os.name == "nt":
        c_temp = Path("C:/Temp/afyaplus_outputs")
        candidates.append((c_temp / subfolder) if subfolder else c_temp)

    candidates.append(preferred)

    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            _real_write_test(candidate)

            if candidate != preferred:
                print(
                    f"⚠️  NOTE: Writing output to:\n    {candidate}\n"
                    f"   instead of the project folder:\n    {preferred}\n"
                    f"   (Kaspersky / Controlled Folder Access workaround "
                    f"— see evaluation/evaluate.py's notes.)\n"
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
    matches = []
    for d in dirs:
        d = Path(d)
        if d.exists():
            matches.extend(d.glob(filename_glob))

    if not matches:
        return None

    return max(matches, key=lambda p: p.stat().st_mtime)


def write_dataframe_csv(dataframe, filepath: Path) -> Path:
    """Write a DataFrame to CSV bypassing pandas' internal file-open
    code path. See module docstring / evaluate.py notes for why.
    Falls back to a folder under C:\\Temp if even that fails.
    """
    filepath = Path(filepath)
    csv_text = dataframe.to_csv(index=False)

    try:
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            f.write(csv_text)
        return filepath

    except (PermissionError, OSError) as e:
        print(f"FAILED SAVE for {filepath}: {e}")
        print("Retrying in fallback location...")

        fallback_dir = (
            Path("C:/Temp/afyaplus_outputs_fallback") if os.name == "nt"
            else Path("/tmp/afyaplus_outputs_fallback")
        )
        fallback_dir.mkdir(parents=True, exist_ok=True)
        fallback_path = fallback_dir / filepath.name

        with open(fallback_path, "w", encoding="utf-8-sig", newline="") as f:
            f.write(csv_text)

        print(f"SUCCESS (fallback): {fallback_path}")
        return fallback_path
