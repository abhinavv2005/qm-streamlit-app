# NovaRetail Customer Intelligence Dashboard
Streamlit dashboard for exploring customer segments, revenue and early-warning signals.

Run locally: `pip install -r requirements.txt && streamlit run app.py`

Deploy: push `app.py`, `requirements.txt`, `NR_dataset.xlsx` to a public GitHub repo, then on share.streamlit.io choose the repo and `app.py`. For the chatbot, add `GROQ_API_KEY = "gsk_..."` under Settings > Secrets (free key at console.groq.com). Without it the chatbot uses built-in rule-based answers.
