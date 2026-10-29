"""Read-only storage inventory and file metadata scanner."""

import logging
import os
from pathlib import Path
from typing import Iterable

import psutil

from .models import DriveInfo, FileFinding, ScanIssue, ScanResult, classify_path

logger = logging.getLogger(__name__)


def default_scan_roots(home: Path | None = None, temp_dir: Path | None = None) -> list[Path]:
    """Return existing, user-scoped roots suitable for a first read-only scan."""
    home = home or Path.home()
    candidates = [home / name for name in ("Desktop", "Downloads", "Documents", "Pictures", "Videos")]
    if temp_dir is not None:
        candidates.append(temp_dir)
    elif os.name == "nt" and os.environ.get("TEMP"):
        candidates.append(Path(os.environ["TEMP"]))
    return list(dict.fromkeys(p.resolve() for p in candidates if p.exists() and p.is_dir()))


def get_drives() -> tuple[DriveInfo, ...]:
    """Read mounted disk capacity without requiring administrator privileges."""
    drives: list[DriveInfo] = []
    for partition in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            drives.append(DriveInfo(partition.mountpoint, partition.fstype, usage.total, usage.used, usage.free))
        except (PermissionError, OSError) as exc:
            logger.info("Cannot read drive %s: %s", partition.mountpoint, exc)
    return tuple(drives)


def scan_roots(roots: Iterable[str | Path], largest_limit: int = 50) -> ScanResult:
    """Scan file sizes and paths only. Never opens, deletes, or modifies file contents."""
    if not isinstance(largest_limit, int) or not 1 <= largest_limit <= 500:
        raise ValueError("largest_limit must be an integer from 1 to 500")

    normalized: list[Path] = []
    for value in roots:
        path = Path(value).expanduser()
        if not path.exists():
            raise ValueError(f"Scan root does not exist: {path}")
        if not path.is_dir():
            raise ValueError(f"Scan root is not a directory: {path}")
        normalized.append(path.resolve())

    issues: list[ScanIssue] = []
    largest: list[FileFinding] = []
    categories: dict[str, int] = {}
    scanned_files = scanned_bytes = 0

    def on_walk_error(exc: OSError) -> None:
        issues.append(ScanIssue(str(getattr(exc, "filename", "unknown")), str(exc)))
        logger.info("Directory scan issue: %s", exc)

    for root in normalized:
        for current, dirs, filenames in os.walk(root, topdown=True, onerror=on_walk_error, followlinks=False):
            # Avoid walking reparse-point/symlink directories to prevent loops and scope escapes.
            current_path = Path(current)
            safe_dirs = []
            for name in dirs:
                candidate = current_path / name
                try:
                    if not candidate.is_symlink():
                        safe_dirs.append(name)
                except OSError as exc:
                    issues.append(ScanIssue(str(candidate), str(exc)))
            dirs[:] = safe_dirs
            for name in filenames:
                file_path = current_path / name
                try:
                    if file_path.is_symlink():
                        continue
                    size = file_path.stat(follow_symlinks=False).st_size
                except (PermissionError, OSError) as exc:
                    issues.append(ScanIssue(str(file_path), str(exc)))
                    continue
                scanned_files += 1
                scanned_bytes += size
                category = classify_path(file_path)
                categories[category] = categories.get(category, 0) + size
                largest.append(FileFinding(str(file_path), size, category))
            # Bound memory while retaining the largest observations.
            if len(largest) > largest_limit * 3:
                largest = sorted(largest, key=lambda item: item.size_bytes, reverse=True)[:largest_limit]

    largest.sort(key=lambda item: item.size_bytes, reverse=True)
    return ScanResult(
        drives=get_drives(), roots=tuple(str(path) for path in normalized), scanned_files=scanned_files,
        scanned_bytes=scanned_bytes, largest_files=tuple(largest[:largest_limit]),
        category_bytes=categories, issues=tuple(issues),
    )
