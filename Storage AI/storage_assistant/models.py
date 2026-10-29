"""Typed data returned by the storage scanner and diagnosis layer."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DriveInfo:
    mountpoint: str
    filesystem: str
    total_bytes: int
    used_bytes: int
    free_bytes: int


@dataclass(frozen=True)
class FileFinding:
    path: str
    size_bytes: int
    category: str


@dataclass(frozen=True)
class ScanIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ScanResult:
    drives: tuple[DriveInfo, ...]
    roots: tuple[str, ...]
    scanned_files: int
    scanned_bytes: int
    largest_files: tuple[FileFinding, ...]
    category_bytes: dict[str, int]
    issues: tuple[ScanIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Recommendation:
    title: str
    explanation: str
    measured_bytes: int
    estimated_recoverable_bytes: int
    risk: str
    source: str


def classify_path(path: Path) -> str:
    """Assign a broad category from the path; this is a hint, not content analysis."""
    parts = {part.casefold() for part in path.parts}
    if "downloads" in parts:
        return "Downloads"
    if "temp" in parts or "tmp" in parts:
        return "Temporary files"
    if "logs" in parts or path.suffix.casefold() == ".log":
        return "Logs"
    if "cache" in parts or "caches" in parts:
        return "Caches"
    return "Other scanned files"
