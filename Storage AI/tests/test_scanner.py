from pathlib import Path

import pytest

from storage_assistant.diagnosis import diagnose
from storage_assistant.scanner import scan_roots


def test_scans_sizes_and_largest_files(tmp_path: Path):
    (tmp_path / "Downloads").mkdir()
    (tmp_path / "Downloads" / "small.txt").write_text("abc", encoding="utf-8")
    (tmp_path / "Downloads" / "large.bin").write_bytes(b"x" * 4096)

    result = scan_roots([tmp_path], largest_limit=1)

    assert result.scanned_files == 2
    assert result.scanned_bytes == 4099
    assert result.largest_files[0].path.endswith("large.bin")
    assert result.category_bytes["Downloads"] == 4099


def test_rejects_invalid_roots_and_limits(tmp_path: Path):
    with pytest.raises(ValueError):
        scan_roots([tmp_path / "missing"])
    with pytest.raises(ValueError):
        scan_roots([tmp_path], largest_limit=0)


def test_diagnosis_does_not_assume_recoverable_savings(tmp_path: Path):
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "data.bin").write_bytes(b"x" * 100)
    result = scan_roots([tmp_path])

    recs = diagnose(result)

    assert recs
    assert all(rec.estimated_recoverable_bytes == 0 for rec in recs)
