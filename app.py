import json
from pathlib import Path

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_json(filepath: Path):
    try:
        with filepath.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        st.error(f"Failed to read JSON: {exc}")
        return None


def to_dataframe(data):
    if data is None:
        return None
    try:
        if isinstance(data, list):
            return pd.json_normalize(data)
        if isinstance(data, dict):
            # Try to find a list-like top-level field
            for key, value in data.items():
                if isinstance(value, list):
                    return pd.json_normalize(value)
            # Fallback: single-row dataframe
            return pd.json_normalize(data)
        return None
    except Exception as exc:
        st.warning(f"Could not convert JSON to table: {exc}")
        return None


def main():
    st.set_page_config(page_title="Question Bank Viewer", layout="wide")
    st.title("Question Bank JSON Viewer")

    default_path = (Path(__file__).parent / "data" / "LinearRegression_quiz.json").resolve()
    st.sidebar.header("Data Sources")

    # Discover JSON files in data directory
    data_dir = default_path.parent
    available_files = sorted([p for p in data_dir.glob("*.json")])
    available_labels = [p.name for p in available_files]

    selected_labels = st.sidebar.multiselect(
        "Select project JSON files",
        options=available_labels,
        default=[default_path.name] if default_path.exists() else [],
    )

    uploads = st.sidebar.file_uploader(
        "Or upload additional JSON files",
        type=["json"],
        accept_multiple_files=True,
    )

    # Load all selected sources
    datasets = []  # list of tuples (label, data_dict)
    for label in selected_labels:
        path = data_dir / label
        if path.exists():
            datasets.append((label, load_json(path)))
        else:
            st.warning(f"Selected file not found: {label}")

    if uploads:
        for uf in uploads:
            try:
                datasets.append((uf.name, json.load(uf)))
            except Exception as exc:
                st.error(f"Failed to parse uploaded JSON {uf.name}: {exc}")

    if not datasets:
        st.info("Select or upload at least one JSON file.")
        return

    source_desc = ", ".join([lbl for lbl, _ in datasets])
    st.caption(f"Sources: {source_desc}")

    # --- Learning Objectives (Top Section) ---
    st.subheader("Learning Objectives")
    for label, d in datasets:
        learning_objectives = d.get("learning_objectives") if isinstance(d, dict) else None
        if isinstance(learning_objectives, dict) and len(learning_objectives) > 0:
            st.markdown(f"**Source:** {label}")
            for module_key, module_info in learning_objectives.items():
                name = module_info.get("name", module_key)
                pages = module_info.get("pages", "-")
                objectives = module_info.get("objectives", [])
                with st.expander(f"{name} (Pages {pages})", expanded=False):
                    if isinstance(objectives, list) and objectives:
                        for obj in objectives:
                            st.markdown(f"- {obj}")
                    else:
                        st.write("No objectives listed.")

    with st.expander("Raw JSON", expanded=False):
        for label, d in datasets:
            st.markdown(f"**{label}**")
            st.json(d)

    # Build questions dataframe from all datasets
    frames = []
    for label, d in datasets:
        if isinstance(d, dict) and isinstance(d.get("questions"), list):
            f = pd.json_normalize(d["questions"])  # more predictable columns
            f["source"] = label
            frames.append(f)

    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not df.empty:

        # Ensure Arrow-friendly types (avoid bools mixed with strings)
        if "correct_answer" in df:
            df["correct_answer"] = df["correct_answer"].astype(str)

        st.subheader("Questions")

        # --- Per-column filters ---
        with st.expander("Filters", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            # String categorical filters
            with col1:
                lesson_name_sel = st.multiselect(
                    "Lesson Name",
                    sorted(df["lesson_name"].dropna().unique()) if "lesson_name" in df else [],
                )
                difficulty_sel = st.multiselect(
                    "Difficulty",
                    sorted(df["difficulty"].dropna().unique()) if "difficulty" in df else [],
                )

            with col2:
                bloom_sel = st.multiselect(
                    "Bloom Level",
                    sorted(df["bloom_level"].dropna().unique()) if "bloom_level" in df else [],
                )
                qtype_sel = st.multiselect(
                    "Question Type",
                    sorted(df["type"].dropna().unique()) if "type" in df else [],
                )

            with col3:
                module_sel = st.multiselect(
                    "Module",
                    sorted(df["module"].dropna().unique()) if "module" in df else [],
                )
                lesson_code_sel = st.multiselect(
                    "Lesson Code",
                    sorted(df["lesson_code"].dropna().unique()) if "lesson_code" in df else [],
                )
                source_sel = st.multiselect(
                    "Source",
                    sorted(df["source"].dropna().unique()) if "source" in df else [],
                )

            # Tags are list-like; collect unique tags safely
            all_tags = set()
            if "tags" in df:
                for entry in df["tags"].dropna():
                    if isinstance(entry, list):
                        all_tags.update([str(t) for t in entry])
                    else:
                        all_tags.add(str(entry))
            with col4:
                tags_sel = st.multiselect("Tags", sorted(all_tags))

            # Text search
            search_text = st.text_input("Search in Question Text", "").strip()

        # Apply filters
        filtered = df.copy()
        def apply_in_filter(frame, column, values):
            if column in frame and values:
                return frame[frame[column].isin(values)]
            return frame

        filtered = apply_in_filter(filtered, "lesson_name", lesson_name_sel)
        filtered = apply_in_filter(filtered, "difficulty", difficulty_sel)
        filtered = apply_in_filter(filtered, "bloom_level", bloom_sel)
        filtered = apply_in_filter(filtered, "type", qtype_sel)
        if "module" in filtered and module_sel:
            # ensure same dtype for comparison
            filtered = filtered[filtered["module"].astype(str).isin([str(m) for m in module_sel])]
        filtered = apply_in_filter(filtered, "lesson_code", lesson_code_sel)
        filtered = apply_in_filter(filtered, "source", source_sel)

        if tags_sel and "tags" in filtered:
            def has_any_tag(x):
                if isinstance(x, list):
                    return any(str(t) in tags_sel for t in x)
                return str(x) in tags_sel
            filtered = filtered[filtered["tags"].apply(has_any_tag)]

        if search_text and "question_text" in filtered:
            filtered = filtered[filtered["question_text"].str.contains(search_text, case=False, na=False)]

        # Display table
        st.dataframe(filtered, use_container_width=True)
        st.download_button(
            label="Download filtered as CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="question_bank_filtered.csv",
            mime="text/csv",
        )

        # --- Export filtered as Markdown ---
        def value(x):
            return "" if pd.isna(x) else str(x)

        def build_markdown(frame: pd.DataFrame) -> str:
            lines = ["# Filtered Questions", ""]
            for _, row in frame.iterrows():
                qid = value(row.get("question_id"))
                lesson = value(row.get("lesson_name"))
                module = value(row.get("module"))
                difficulty = value(row.get("difficulty"))
                bloom = value(row.get("bloom_level"))
                qtype = value(row.get("type"))
                text = value(row.get("question_text"))
                page_ref = value(row.get("page_reference"))
                src = value(row.get("source"))

                header = f"### {qid} — {lesson} (Module {module}) [{difficulty} | {bloom}]"
                lines.append(header)
                if src:
                    lines.append(f"- Source: {src}")
                if page_ref:
                    lines.append(f"- Page(s): {page_ref}")
                lines.append(f"- Type: {qtype}")
                lines.append("")
                lines.append(text)
                lines.append("")

                # Options if present (multiple_choice)
                opts = []
                for key in ["A", "B", "C", "D"]:
                    col = f"options.{key}"
                    if col in frame.columns:
                        val = value(row.get(col))
                        if val:
                            opts.append(f"- {key}: {val}")
                if opts:
                    lines.append("Options:")
                    lines.extend(opts)
                    lines.append("")

                answer = value(row.get("correct_answer"))
                if answer != "":
                    lines.append(f"- Answer: {answer}")

                expl = value(row.get("explanation"))
                if expl:
                    lines.append(f"- Explanation: {expl}")

                tags_val = row.get("tags")
                if isinstance(tags_val, list) and tags_val:
                    lines.append(f"- Tags: {', '.join(str(t) for t in tags_val)}")

                lines.append("")
            return "\n".join(lines)

        md_content = build_markdown(filtered)
        st.download_button(
            label="Download filtered as Markdown",
            data=md_content.encode("utf-8"),
            file_name="question_bank_filtered.md",
            mime="text/markdown",
        )

        # --- Selection of questions and Selected table ---
        st.subheader("Select Questions")

        if "selected_ids" not in st.session_state:
            st.session_state["selected_ids"] = set()

        selected_ids = st.session_state["selected_ids"]

        # Bulk actions
        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button("Select all filtered"):
                ids = (
                    filtered.get("question_id", pd.Series(dtype=str)).astype(str)
                    + "::"
                    + filtered.get("source", pd.Series(dtype=str)).astype(str)
                )
                selected_ids.update(ids.tolist())
        with bcol2:
            if st.button("Clear filtered from selection"):
                visible = set(
                    (
                        filtered.get("question_id", pd.Series(dtype=str)).astype(str)
                        + "::"
                        + filtered.get("source", pd.Series(dtype=str)).astype(str)
                    ).tolist()
                )
                selected_ids.difference_update(visible)
        with bcol3:
            if st.button("Clear ALL selections"):
                selected_ids.clear()

        st.caption("Toggle checkboxes to add/remove individual questions.")

        # Checkbox grid for current filtered rows
        # Show compact controls: checkbox + id + (truncated) text
        for _, row in filtered.iterrows():
            qid = str(row.get("question_id", ""))
            if qid == "":
                continue
            src = str(row.get("source", ""))
            selection_id = f"{qid}::{src}" if src else qid
            question_preview = str(row.get("question_text", "")).strip().replace("\n", " ")
            if len(question_preview) > 120:
                question_preview = question_preview[:117] + "..."
            checked_before = selection_id in selected_ids
            checked_now = st.checkbox(
                f"[{src}] {qid}: {question_preview}",
                value=checked_before,
                key=f"select_{selection_id}",
            )
            if checked_now and not checked_before:
                selected_ids.add(selection_id)
            elif not checked_now and checked_before:
                selected_ids.discard(selection_id)

        # Persist updates
        st.session_state["selected_ids"] = selected_ids

        # Selected table
        st.subheader(f"Selected Questions ({len(selected_ids)})")
        if len(selected_ids) > 0:
            # Split selection_id back to (qid, source)
            sel_pairs = [s.split("::", 1) if "::" in s else [s, ""] for s in selected_ids]
            sel_df = pd.DataFrame(sel_pairs, columns=["question_id", "source"]) if sel_pairs else pd.DataFrame(columns=["question_id", "source"])
            selected_df = df.merge(
                sel_df,
                on=["question_id", "source"],
                how="inner",
            )
            st.dataframe(selected_df, use_container_width=True)

            # Export selected as Markdown
            md_selected = build_markdown(selected_df)
            st.download_button(
                label="Download selected as Markdown",
                data=md_selected.encode("utf-8"),
                file_name="question_bank_selected.md",
                mime="text/markdown",
            )
        else:
            st.info("No questions selected yet.")
    else:
        st.info("Could not render a table. See raw JSON above.")


if __name__ == "__main__":
    main()


