# Laptop Storage Assistant (read-only MVP)

## Architecture

- `storage_assistant/scanner.py` reads mounted-drive capacity and file metadata under selected roots. It skips symbolic links and records access errors.
- `storage_assistant/models.py` defines structured scan results and findings.
- `storage_assistant/diagnosis.py` makes conservative, deterministic observations. It reports measured sizes and does not claim they are recoverable.
- `storage_assistant/llm.py` optionally asks an LLM to explain scan data. Its output is text only and is never executed.
- `app.py` presents the scan and diagnosis in Streamlit. Cleanup controls are deliberately disabled.

The first release is read-only. Later cleanup work should use a fixed allowlist, an explicit preview and confirmation, and a post-action rescan. Never accept LLM-generated commands or delete unknown/personal files automatically.

## Setup (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
streamlit run app.py
```

Add `OPENAI_API_KEY` to `.env` to enable optional explanation. Do not commit `.env`.

## Tests

```powershell
python -m pytest -q
```

The tests use temporary directories and do not touch real user data.

## Windows notes

The app does not require administrator privileges for ordinary scans. Windows may deny access to protected folders; these are reported as scan issues. Drive readings come from `psutil` and can include mounted volumes that are unavailable at scan time. The default scan roots are selected user folders and `%TEMP%`; add or remove roots in the sidebar. File categories are inferred from path names and extensions, not file contents. This MVP does not scan the Recycle Bin, protected system folders, or application data by default.
