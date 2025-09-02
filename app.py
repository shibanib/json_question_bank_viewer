import json
from pathlib import Path

import pandas as pd
import streamlit as st


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

    default_path = Path("data/LinearRegression_quiz.json")
    st.sidebar.header("Data Source")

    use_project_file = st.sidebar.checkbox(
        "Use project JSON file (data/LinearRegression_quiz.json)", value=True
    )

    uploaded_file = None
    if not use_project_file:
        uploaded_file = st.sidebar.file_uploader("Upload a JSON file", type=["json"]) 

    data = None
    source_desc = ""
    if use_project_file:
        if default_path.exists():
            data = load_json(default_path)
            source_desc = str(default_path)
        else:
            st.error(f"Default file not found at {default_path}")
    else:
        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                source_desc = uploaded_file.name
            except Exception as exc:
                st.error(f"Failed to parse uploaded JSON: {exc}")

    if data is None:
        st.info("Provide a valid JSON file to view its contents.")
        return

    st.caption(f"Source: {source_desc}")

    with st.expander("Raw JSON", expanded=False):
        st.json(data)

    df = to_dataframe(data)
    if df is not None and not df.empty:
        st.subheader("Tabular View")
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="question_bank.csv",
            mime="text/csv",
        )
    else:
        st.info("Could not render a table. See raw JSON above.")


if __name__ == "__main__":
    main()


