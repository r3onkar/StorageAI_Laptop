"""Conservative, deterministic explanations based on measured scan data."""

from .models import Recommendation, ScanResult


def diagnose(result: ScanResult, low_space_percent: float = 15.0) -> list[Recommendation]:
    if not 0 <= low_space_percent <= 100:
        raise ValueError("low_space_percent must be between 0 and 100")
    recommendations: list[Recommendation] = []
    for drive in result.drives:
        free_pct = (drive.free_bytes / drive.total_bytes * 100) if drive.total_bytes else 0
        if free_pct < low_space_percent:
            recommendations.append(Recommendation(
                title=f"Low free space on {drive.mountpoint}",
                explanation=f"The drive has {free_pct:.1f}% free ({drive.free_bytes:,} bytes). This is a measured capacity reading.",
                measured_bytes=drive.used_bytes,
                estimated_recoverable_bytes=0,
                risk="Informational; no files were inspected or changed by this finding.",
                source="Drive capacity measurement",
            ))
    for category, size in sorted(result.category_bytes.items(), key=lambda item: item[1], reverse=True):
        if size == 0:
            continue
        share = size / result.scanned_bytes * 100 if result.scanned_bytes else 0
        recommendations.append(Recommendation(
            title=f"Review {category.lower()} ({size:,} bytes scanned)",
            explanation=f"This category accounts for {share:.1f}% of bytes in the selected scan roots. The scan measured file sizes only.",
            measured_bytes=size,
            estimated_recoverable_bytes=0,
            risk="Unknown until individual files are reviewed; no savings are assumed.",
            source="Path-based category estimate",
        ))
    return recommendations
