# Question Bank Viewer

A simple Streamlit app to view and tabulate JSON question bank data from `data/`.

## Setup

1. Create and activate the environment (uv):

```bash
cd /Users/shibanibudhraja/Downloads/Question_Bank
uv venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
uv pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
streamlit run app.py
```

The app will default to `data/LinearRegression_quiz.json`, or you can upload another JSON.

## Developing

Add new features in `app.py`. Keep data files in `data/`.


