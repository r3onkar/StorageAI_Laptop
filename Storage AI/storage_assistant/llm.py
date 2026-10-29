"""Optional LLM explanation adapter. Its output is explanatory text only."""

import json
import logging
import os

from .models import ScanResult

logger = logging.getLogger(__name__)


def explain_with_llm(result: ScanResult) -> str | None:
    """Ask OpenAI for a concise interpretation; returns None when unconfigured/unavailable."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        # Send only aggregate measurements and sizes. Absolute paths and filenames can
        # contain personal information, so they stay on the user's machine.
        safe_summary = {
            "drives": [
                {"mountpoint": d.mountpoint, "filesystem": d.filesystem,
                 "total_bytes": d.total_bytes, "used_bytes": d.used_bytes, "free_bytes": d.free_bytes}
                for d in result.drives
            ],
            "scanned_file_count": result.scanned_files,
            "scanned_bytes": result.scanned_bytes,
            "category_bytes": result.category_bytes,
            "largest_file_sizes_bytes": [f.size_bytes for f in result.largest_files],
            "issue_count": len(result.issues),
        }
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=[
                {"role": "system", "content": "Explain this read-only storage scan. Separate measured facts from cautious inferences. Do not suggest commands or claim files are safe to delete."},
                {"role": "user", "content": json.dumps(safe_summary, ensure_ascii=False)},
            ],
        )
        return response.output_text.strip()
    except Exception:
        logger.exception("Optional LLM explanation failed")
        return "AI explanation is unavailable. The measured scan and local diagnosis remain available."
