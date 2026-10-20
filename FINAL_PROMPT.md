# Final prompt used (vibe coding)

Build a Python Streamlit dashboard (`app.py`) for NovaRetail, a nationwide omnichannel retailer, for Sophia Martinez, Director of Customer Intelligence. The app will be stored in a GitHub repository (with `app.py`, `requirements.txt` and `NR_dataset.xlsx` in the repo root) and deployed publicly on Streamlit Community Cloud, so use relative file paths, `st.cache_data`, and only libraries listed in `requirements.txt` (streamlit, pandas, plotly, openpyxl, requests).

**Data:** `NR_dataset.xlsx` (sheet `data`, 100 transactions, 34 customers). Columns used: label (Promising/Growth/Stable/Decline, assigned per transaction), CustomerID, TransactionDate, ProductCategory, PurchaseAmount, CustomerAgeGroup, CustomerGender, CustomerRegion, CustomerSatisfaction (1-5), RetailChannel. Ignore idx and TransactionID (not unique). Clean it: group the 34 free-text product names into ~9 categories, merge age groups "55+" and "55-64", show the one missing label as "Unlabeled".

**Goals the dashboard must support:** (a) find growth opportunities in the existing customer base, (b) detect early warning signs of customer decline or reduced engagement, (c) support data-driven commercial and marketing priorities.

**Layout:** sidebar filters (segment, region, category, channel, age group, gender, date range, satisfaction range) that drive everything; a KPI row (total revenue, transactions, unique customers, average purchase, average satisfaction, share of revenue in Decline); then tabs:
1. Overview: revenue by segment, region, category, channel x segment, weekly revenue by segment.
2. Growth opportunities: category x segment heatmap, region x channel heatmap for Growth + Promising, average purchase by segment, Growth + Promising revenue by age group, plus an auto-generated one-line takeaway.
3. Early warnings: satisfaction by segment and rating distribution, Decline revenue by region and category, KPIs for low-satisfaction (<=2) revenue, and a watch list table of the largest unhappy purchases.
4. Data: filtered table, CSV download, and a short data-quality notes box.
5. Ask the assistant: an AI chatbot (Groq, model llama-3.3-70b-versatile, key from `st.secrets["GROQ_API_KEY"]` or an optional password input) that answers using a compact summary of the currently filtered data as context, quotes exact figures, and says when the data cannot answer. If no key or the API call fails, fall back to rule-based answers computed from the filtered data so the tab never breaks.

**Design:** consistent segment colors (Promising blue, Growth green, Stable gray, Decline red), clean wide layout, plain-language titles, and a friendly message when filters return no rows. Note that the sample covers only ~5 weeks so trends are directional.

Return the complete `app.py` and `requirements.txt`, plus step-by-step instructions to push to GitHub and deploy on Streamlit Community Cloud (including adding GROQ_API_KEY under app Secrets).
