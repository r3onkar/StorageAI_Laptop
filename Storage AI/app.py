"""Streamlit dashboard for the read-only storage assistant MVP."""

import logging
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from storage_assistant.diagnosis import diagnose
from storage_assistant.llm import explain_with_llm
from storage_assistant.scanner import default_scan_roots, scan_roots

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

st.set_page_config(page_title="Laptop Storage Assistant", page_icon="💽", layout="wide")
st.title("Laptop Storage Assistant")
st.caption("Read-only MVP · inspects file paths and sizes only · no cleanup actions are available")

if "scan_result" not in st.session_state:
    st.session_state.scan_result = None
if "diagnosed" not in st.session_state:
    st.session_state.diagnosed = False

with st.sidebar:
    st.header("Scan settings")
    defaults = default_scan_roots()
    roots_text = st.text_area("Folders to scan (one path per line)", value="\n".join(map(str, defaults)), height=180)
    threshold = st.slider("Low-space alert threshold (%)", min_value=1, max_value=50, value=15)
    st.caption("Choose folders you can access. Scanning may take time for large folders.")

scan_col, diagnose_col, preview_col, confirm_col = st.columns(4)
with scan_col:
    scan_clicked = st.button("Scan", type="primary", use_container_width=True)
with diagnose_col:
    diagnose_clicked = st.button("Diagnose", use_container_width=True, disabled=st.session_state.scan_result is None)
with preview_col:
    st.button("Preview Cleanup", use_container_width=True, disabled=True, help="Cleanup is not implemented in this read-only MVP.")
with confirm_col:
    st.button("Confirm Cleanup", use_container_width=True, disabled=True, help="Cleanup is not implemented in this read-only MVP.")

if scan_clicked:
    try:
        roots = [Path(line.strip()).expanduser() for line in roots_text.splitlines() if line.strip()]
        if not roots:
            raise ValueError("Add at least one folder to scan.")
        with st.spinner("Reading storage metadata…"):
            st.session_state.scan_result = scan_roots(roots)
            st.session_state.diagnosed = False
        st.success("Scan complete. No files were changed.")
    except (OSError, ValueError) as exc:
        st.error(str(exc))

result = st.session_state.scan_result
if result is not None:
    drives = result.drives
    if drives:
        st.subheader("Drive capacity")
        for drive in drives:
            st.write(f"**{drive.mountpoint}** · {drive.filesystem or 'unknown filesystem'}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total", f"{drive.total_bytes / 2**30:.2f} GiB")
            c2.metric("Used", f"{drive.used_bytes / 2**30:.2f} GiB")
            c3.metric("Free", f"{drive.free_bytes / 2**30:.2f} GiB")
            pct = 100 * drive.free_bytes / drive.total_bytes if drive.total_bytes else 0
            c4.metric("Free percent", f"{pct:.1f}%", delta="Low" if pct < threshold else None, delta_color="inverse")
            st.progress(max(0.0, min(1.0, 1 - pct / 100)), text="Used capacity")
    else:
        st.info("No accessible mounted drives were returned by the system.")

    st.subheader("Scan summary")
    a, b, c = st.columns(3)
    a.metric("Files measured", f"{result.scanned_files:,}")
    b.metric("Bytes in scanned roots", f"{result.scanned_bytes / 2**30:.2f} GiB")
    c.metric("Skipped / inaccessible entries", f"{len(result.issues):,}")
    st.caption("Directory totals are sums of file sizes in selected roots; they may not match drive usage due to unscanned locations, sparse/compressed files, and filesystem accounting.")

    st.subheader("Largest files")
    if result.largest_files:
        st.dataframe([{"Path": f.path, "Size (MiB)": round(f.size_bytes / 2**20, 2), "Category": f.category} for f in result.largest_files], use_container_width=True, hide_index=True)
    else:
        st.info("No files were found in the selected roots.")

    st.subheader("Category totals")
    if result.category_bytes:
        st.bar_chart({name: size / 2**30 for name, size in result.category_bytes.items()}, y_label="GiB")
    recommendations = diagnose(result, threshold)
    if diagnose_clicked:
        st.session_state.diagnosed = True
    if st.session_state.diagnosed:
        st.subheader("Local diagnosis")
        if recommendations:
            for item in recommendations:
                st.markdown(f"**{item.title}**  \n{item.explanation}  \nRisk: {item.risk}")
        else:
            st.info("No low-space alert or non-empty scan category was found.")

    if st.button("Ask AI to explain this scan"):
        with st.spinner("Preparing optional AI explanation…"):
            explanation = explain_with_llm(result)
        if explanation:
            st.subheader("AI explanation")
            st.write(explanation)
        else:
            st.info("AI is not configured. Set OPENAI_API_KEY in your environment to enable optional explanations.")

    with st.expander("Scan issues"):
        if result.issues:
            st.dataframe([{"Path": issue.path, "Issue": issue.message} for issue in result.issues], use_container_width=True, hide_index=True)
        else:
            st.write("No access errors were reported.")
