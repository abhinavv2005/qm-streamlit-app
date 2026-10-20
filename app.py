"""NovaRetail Customer Intelligence Dashboard.

Streamlit app for Sophia Martinez (Director of Customer Intelligence).
Deploy: push this repo to GitHub, then create the app on Streamlit Community Cloud.
Chatbot: Groq (free tier). Add GROQ_API_KEY under Settings > Secrets. Without a key,
the assistant falls back to built-in rule-based answers computed from the filtered data.
"""

import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="NovaRetail Customer Intelligence", page_icon="📊", layout="wide")

DATA_FILE = Path(__file__).parent / "NR_dataset.xlsx"
SEGMENTS = ["Promising", "Growth", "Stable", "Decline"]
SEG_COLORS = {
    "Promising": "#2563EB",
    "Growth": "#16A34A",
    "Stable": "#94A3B8",
    "Decline": "#DC2626",
    "Unlabeled": "#CBD5E1",
}

# The raw file has 34 free-text category names; group them into 9 readable ones.
CATEGORY_MAP = {
    "Electronics": "Electronics", "Gaming": "Electronics",
    "Clothing": "Clothing & Fashion", "Fashion": "Clothing & Fashion",
    "Fashion & Apparel": "Clothing & Fashion", "Fashion Accessories": "Clothing & Fashion",
    "Children's Clothing": "Clothing & Fashion",
    "Groceries": "Groceries & Food", "Grocery": "Groceries & Food",
    "Grocery Items": "Groceries & Food", "Food & Beverages": "Groceries & Food",
    "Books": "Books", "Books & Magazines": "Books",
    "Home Appliances": "Home & Furniture", "Home Decor": "Home & Furniture",
    "Home & Garden": "Home & Furniture", "Home Improvement": "Home & Furniture",
    "Furniture": "Home & Furniture", "Furniture & Decor": "Home & Furniture",
    "Gardening Tools": "Home & Furniture",
    "Health & Wellness": "Health & Beauty", "Health & Beauty": "Health & Beauty",
    "Health Supplements": "Health & Beauty", "Beauty Products": "Health & Beauty",
    "Beauty & Personal Care": "Health & Beauty", "Cosmetics": "Health & Beauty",
    "Sporting Goods": "Sports & Outdoors", "Sports & Outdoors": "Sports & Outdoors",
    "Sports Equipment": "Sports & Outdoors", "Outdoor Equipment": "Sports & Outdoors",
    "Sportswear": "Sports & Outdoors",
    "Toys": "Toys & Games", "Toys & Games": "Toys & Games",
    "Office Supplies": "Other", "Automotive": "Other",
}


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_excel(DATA_FILE)
    df["TransactionDate"] = pd.to_datetime(df["TransactionDate"])
    df["label"] = df["label"].fillna("Unlabeled")
    df["Category"] = df["ProductCategory"].map(CATEGORY_MAP).fillna("Other")
    df["CustomerAgeGroup"] = df["CustomerAgeGroup"].replace({"55+": "55+", "55-64": "55+"})
    df["Week"] = df["TransactionDate"].dt.to_period("W-SUN").dt.start_time
    df["LowSat"] = df["CustomerSatisfaction"] <= 2
    return df


def money(x: float) -> str:
    return f"${x:,.0f}"


def style(fig, height=340):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", y=-0.2), title_font_size=15,
    )
    return fig


raw = load_data()

# ----------------------------------------------------------------- Sidebar filters
st.sidebar.title("Filters")
seg_opts = [s for s in SEGMENTS + ["Unlabeled"] if s in raw["label"].unique()]
f_seg = st.sidebar.multiselect("Customer segment", seg_opts, default=seg_opts)
f_region = st.sidebar.multiselect("Region", sorted(raw["CustomerRegion"].unique()), default=sorted(raw["CustomerRegion"].unique()))
f_cat = st.sidebar.multiselect("Product category", sorted(raw["Category"].unique()), default=sorted(raw["Category"].unique()))
f_chan = st.sidebar.multiselect("Retail channel", sorted(raw["RetailChannel"].unique()), default=sorted(raw["RetailChannel"].unique()))
age_order = sorted(raw["CustomerAgeGroup"].unique())
f_age = st.sidebar.multiselect("Age group", age_order, default=age_order)
f_gender = st.sidebar.multiselect("Gender", sorted(raw["CustomerGender"].unique()), default=sorted(raw["CustomerGender"].unique()))
dmin, dmax = raw["TransactionDate"].min().date(), raw["TransactionDate"].max().date()
f_date = st.sidebar.date_input("Transaction dates", (dmin, dmax), min_value=dmin, max_value=dmax)
f_sat = st.sidebar.slider("Satisfaction rating", 1, 5, (1, 5))

df = raw[
    raw["label"].isin(f_seg) & raw["CustomerRegion"].isin(f_region) & raw["Category"].isin(f_cat)
    & raw["RetailChannel"].isin(f_chan) & raw["CustomerAgeGroup"].isin(f_age)
    & raw["CustomerGender"].isin(f_gender)
    & raw["CustomerSatisfaction"].between(*f_sat)
]
if isinstance(f_date, (tuple, list)) and len(f_date) == 2:
    df = df[df["TransactionDate"].dt.date.between(f_date[0], f_date[1])]

st.title("NovaRetail Customer Intelligence")
st.caption(
    "Where is revenue coming from, which segments are slipping, and where should we invest? "
    "Use the sidebar to slice the data; every chart, table and the chatbot follow your filters."
)

if df.empty:
    st.warning("No transactions match the current filters. Widen the filters in the sidebar.")
    st.stop()

# ----------------------------------------------------------------- KPIs
total_rev = df["PurchaseAmount"].sum()
decline_rev = df.loc[df["label"] == "Decline", "PurchaseAmount"].sum()
growth_rev = df.loc[df["label"].isin(["Growth", "Promising"]), "PurchaseAmount"].sum()
c = st.columns(6)
c[0].metric("Total revenue", money(total_rev))
c[1].metric("Transactions", f"{len(df):,}")
c[2].metric("Unique customers", f"{df['CustomerID'].nunique():,}")
c[3].metric("Avg purchase", f"${df['PurchaseAmount'].mean():,.2f}")
c[4].metric("Avg satisfaction", f"{df['CustomerSatisfaction'].mean():.2f} / 5")
c[5].metric("Revenue in Decline", f"{decline_rev / total_rev:.0%}", help="Share of filtered revenue from transactions labeled Decline")

tab_over, tab_growth, tab_risk, tab_data, tab_chat = st.tabs(
    ["Overview", "Growth opportunities", "Early warnings", "Data", "Ask the assistant"]
)

# ----------------------------------------------------------------- Overview
with tab_over:
    a, b = st.columns(2)
    seg = df.groupby("label", as_index=False).agg(Revenue=("PurchaseAmount", "sum"), Transactions=("idx", "count"))
    a.plotly_chart(style(px.bar(seg, x="label", y="Revenue", color="label", color_discrete_map=SEG_COLORS,
                                text_auto="$,.0f", title="Revenue by segment").update_layout(showlegend=False, xaxis_title=None)), width='stretch')
    reg = df.groupby("CustomerRegion", as_index=False)["PurchaseAmount"].sum()
    b.plotly_chart(style(px.bar(reg.sort_values("PurchaseAmount", ascending=False), x="CustomerRegion", y="PurchaseAmount",
                                text_auto="$,.0f", title="Revenue by region").update_layout(xaxis_title=None, yaxis_title="Revenue")), width='stretch')
    a, b = st.columns(2)
    cat = df.groupby("Category", as_index=False)["PurchaseAmount"].sum().sort_values("PurchaseAmount")
    a.plotly_chart(style(px.bar(cat, x="PurchaseAmount", y="Category", orientation="h", text_auto="$,.0f",
                                title="Revenue by product category").update_layout(yaxis_title=None, xaxis_title="Revenue")), width='stretch')
    ch = df.groupby(["RetailChannel", "label"], as_index=False)["PurchaseAmount"].sum()
    b.plotly_chart(style(px.bar(ch, x="RetailChannel", y="PurchaseAmount", color="label", color_discrete_map=SEG_COLORS,
                                barmode="stack", title="Revenue by channel and segment").update_layout(xaxis_title=None, yaxis_title="Revenue", legend_title=None)), width='stretch')
    wk = df.groupby(["Week", "label"], as_index=False)["PurchaseAmount"].sum()
    st.plotly_chart(style(px.line(wk, x="Week", y="PurchaseAmount", color="label", color_discrete_map=SEG_COLORS, markers=True,
                                  title="Weekly revenue by segment").update_layout(yaxis_title="Revenue", xaxis_title=None, legend_title=None), 320), width='stretch')
    st.caption("Data covers only about five weeks (Jan 15 – Feb 20, 2023), so weekly trends are directional, not statistical.")

# ----------------------------------------------------------------- Growth
with tab_growth:
    st.subheader("Where is growth coming from, and where can we push it?")
    grow = df[df["label"].isin(["Growth", "Promising"])]
    if grow.empty:
        st.info("No Growth or Promising transactions in the current filter.")
    else:
        a, b = st.columns(2)
        heat = df.pivot_table(index="Category", columns="label", values="PurchaseAmount", aggfunc="sum", fill_value=0)
        heat = heat[[s for s in SEG_COLORS if s in heat.columns]]
        a.plotly_chart(style(px.imshow(heat, text_auto="$,.0f", aspect="auto", color_continuous_scale="Blues",
                                       title="Revenue: category × segment"), 380), width='stretch')
        rc = grow.pivot_table(index="CustomerRegion", columns="RetailChannel", values="PurchaseAmount", aggfunc="sum", fill_value=0)
        b.plotly_chart(style(px.imshow(rc, text_auto="$,.0f", aspect="auto", color_continuous_scale="Greens",
                                       title="Growth + Promising revenue: region × channel"), 380), width='stretch')
        a, b = st.columns(2)
        aov = df.groupby("label", as_index=False).agg(AvgPurchase=("PurchaseAmount", "mean"), Satisfaction=("CustomerSatisfaction", "mean"))
        a.plotly_chart(style(px.bar(aov, x="label", y="AvgPurchase", color="label", color_discrete_map=SEG_COLORS, text_auto="$,.0f",
                                    title="Average purchase by segment").update_layout(showlegend=False, xaxis_title=None, yaxis_title="Avg purchase")), width='stretch')
        age = grow.groupby("CustomerAgeGroup", as_index=False)["PurchaseAmount"].sum()
        b.plotly_chart(style(px.bar(age, x="CustomerAgeGroup", y="PurchaseAmount", text_auto="$,.0f",
                                    title="Growth + Promising revenue by age group").update_layout(xaxis_title=None, yaxis_title="Revenue")), width='stretch')
        top = grow.groupby("Category")["PurchaseAmount"].sum().sort_values(ascending=False)
        st.info(
            f"Growth + Promising customers generate {money(growth_rev)} ({growth_rev / total_rev:.0%} of filtered revenue). "
            f"Top category: {top.index[0]} ({money(top.iloc[0])}). Best region × channel cell: "
            f"{rc.stack().idxmax()[0]} / {rc.stack().idxmax()[1]} ({money(rc.stack().max())})."
        )

# ----------------------------------------------------------------- Early warnings
with tab_risk:
    st.subheader("Early warning signs of decline or reduced engagement")
    sat = df.groupby("label", as_index=False).agg(Satisfaction=("CustomerSatisfaction", "mean"), LowSatShare=("LowSat", "mean"))
    a, b = st.columns(2)
    a.plotly_chart(style(px.bar(sat, x="label", y="Satisfaction", color="label", color_discrete_map=SEG_COLORS, text_auto=".2f",
                                title="Average satisfaction by segment").update_layout(showlegend=False, xaxis_title=None, yaxis_range=[0, 5])), width='stretch')
    dist = df.groupby(["CustomerSatisfaction", "label"], as_index=False).size()
    b.plotly_chart(style(px.bar(dist, x="CustomerSatisfaction", y="size", color="label", color_discrete_map=SEG_COLORS, barmode="stack",
                                title="Satisfaction rating distribution").update_layout(yaxis_title="Transactions", legend_title=None)), width='stretch')

    dec = df[df["label"] == "Decline"]
    at_risk = df[df["LowSat"]]
    k = st.columns(3)
    k[0].metric("Decline transactions", f"{len(dec)}", help="Transactions labeled Decline in the current filter")
    k[1].metric("Revenue with satisfaction ≤ 2", money(at_risk["PurchaseAmount"].sum()),
                f"{at_risk['PurchaseAmount'].sum() / total_rev:.0%} of revenue", delta_color="off")
    k[2].metric("Low-satisfaction share of all transactions", f"{df['LowSat'].mean():.0%}")

    if dec.empty:
        st.info("No Decline transactions in the current filter.")
    else:
        a, b = st.columns(2)
        dr = dec.groupby("CustomerRegion", as_index=False).agg(Revenue=("PurchaseAmount", "sum"), Satisfaction=("CustomerSatisfaction", "mean"))
        a.plotly_chart(style(px.bar(dr, x="CustomerRegion", y="Revenue", text_auto="$,.0f", color_discrete_sequence=[SEG_COLORS["Decline"]],
                                    title="Decline revenue by region").update_layout(xaxis_title=None)), width='stretch')
        dc = dec.groupby("Category", as_index=False)["PurchaseAmount"].sum().sort_values("PurchaseAmount")
        b.plotly_chart(style(px.bar(dc, x="PurchaseAmount", y="Category", orientation="h", text_auto="$,.0f", color_discrete_sequence=[SEG_COLORS["Decline"]],
                                    title="Decline revenue by category").update_layout(yaxis_title=None, xaxis_title="Revenue")), width='stretch')

    st.markdown("**Watch list: unhappy, high-value purchases (satisfaction ≤ 2, largest first)**")
    watch = at_risk.sort_values("PurchaseAmount", ascending=False)[
        ["TransactionDate", "CustomerID", "label", "Category", "PurchaseAmount", "CustomerSatisfaction", "CustomerRegion", "RetailChannel"]
    ].head(15)
    st.dataframe(watch.rename(columns={"label": "Segment", "CustomerSatisfaction": "Satisfaction"}), hide_index=True, width='stretch',
                 column_config={"PurchaseAmount": st.column_config.NumberColumn("Amount", format="$%.2f"),
                                "TransactionDate": st.column_config.DateColumn("Date")})

# ----------------------------------------------------------------- Data
with tab_data:
    st.dataframe(df.drop(columns=["Week", "LowSat"]), hide_index=True, width='stretch')
    st.download_button("Download filtered data (CSV)", df.drop(columns=["Week", "LowSat"]).to_csv(index=False), "novaretail_filtered.csv", "text/csv")
    with st.expander("Data notes"):
        st.markdown(
            "- The segment label is assigned **per transaction**, so one customer can appear in several segments.\n"
            "- 34 raw product names were grouped into 9 categories; ages `55+` and `55-64` were merged.\n"
            "- One transaction has no segment label and is shown as *Unlabeled*.\n"
            "- `TransactionID` is not unique (several rows share the same ID), so it is not used as a key.\n"
            "- The sample is small (100 rows, 34 customers), so treat patterns as directional."
        )

# ----------------------------------------------------------------- Chatbot
def build_context(d: pd.DataFrame) -> str:
    def tbl(g, col="PurchaseAmount"):
        t = d.groupby(g).agg(revenue=(col, "sum"), transactions=("idx", "count"), avg_purchase=(col, "mean"),
                             avg_satisfaction=("CustomerSatisfaction", "mean")).round(2).sort_values("revenue", ascending=False)
        return t.to_string()

    return (
        f"Filtered data: {len(d)} transactions, {d['CustomerID'].nunique()} customers, total revenue ${d['PurchaseAmount'].sum():,.2f}, "
        f"dates {d['TransactionDate'].min().date()} to {d['TransactionDate'].max().date()}.\n"
        f"Active filters: segments={f_seg}, regions={f_region}, channels={f_chan}, age={f_age}, gender={f_gender}, satisfaction={f_sat}.\n\n"
        f"By segment:\n{tbl('label')}\n\nBy category:\n{tbl('Category')}\n\nBy region:\n{tbl('CustomerRegion')}\n\n"
        f"By channel:\n{tbl('RetailChannel')}\n\nBy age group:\n{tbl('CustomerAgeGroup')}\n\nBy gender:\n{tbl('CustomerGender')}\n\n"
        f"Segment x region revenue:\n{d.pivot_table(index='label', columns='CustomerRegion', values='PurchaseAmount', aggfunc='sum', fill_value=0).round(0).to_string()}\n\n"
        f"Segment x channel revenue:\n{d.pivot_table(index='label', columns='RetailChannel', values='PurchaseAmount', aggfunc='sum', fill_value=0).round(0).to_string()}\n\n"
        f"Revenue with satisfaction <=2: ${d.loc[d['LowSat'], 'PurchaseAmount'].sum():,.2f} across {int(d['LowSat'].sum())} transactions.\n"
        f"Notes: segment labels are per transaction; Decline = customers whose purchasing is falling; the sample covers ~5 weeks only."
    )


def fallback_answer(q: str, d: pd.DataFrame) -> str:
    ql = q.lower()
    tot = d["PurchaseAmount"].sum()

    def top(col, label):
        s = d.groupby(col)["PurchaseAmount"].sum().sort_values(ascending=False)
        return f"Top {label} by revenue: **{s.index[0]}** ({money(s.iloc[0])}, {s.iloc[0] / tot:.0%}), then {s.index[1]} ({money(s.iloc[1])})." if len(s) > 1 else f"Only {s.index[0]} ({money(s.iloc[0])}) in the current filter."

    if "region" in ql:
        return top("CustomerRegion", "region")
    if "categor" in ql or "product" in ql:
        return top("Category", "category")
    if "channel" in ql or "online" in ql or "store" in ql:
        return top("RetailChannel", "channel")
    if "age" in ql:
        return top("CustomerAgeGroup", "age group")
    if "gender" in ql:
        return top("CustomerGender", "gender")
    if "satisf" in ql or "decline" in ql or "risk" in ql or "churn" in ql:
        s = d.groupby("label")["CustomerSatisfaction"].mean().round(2).to_dict()
        low = d.loc[d["LowSat"], "PurchaseAmount"].sum()
        return f"Average satisfaction by segment: {s}. Revenue from purchases rated 2 or lower: {money(low)} ({low / tot:.0%} of revenue)."
    if "segment" in ql or "revenue" in ql or "customer" in ql:
        return top("label", "segment")
    return ("I can answer questions about revenue by segment, region, category, channel, age or gender, and about satisfaction and decline risk. "
            "Add a free Groq API key in the app secrets for open-ended answers.")


with tab_chat:
    st.subheader("Ask about what you see")
    st.caption("Answers use the currently filtered data. Powered by Groq when a key is configured; otherwise built-in rule-based answers.")
    try:
        key = st.secrets["GROQ_API_KEY"]
    except Exception:
        key = ""
    model = "llama-3.3-70b-versatile"
    if not key:
        key = st.text_input("Groq API key (optional, free at console.groq.com)", type="password")

    if "chat" not in st.session_state:
        st.session_state.chat = []
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])

    q = st.chat_input("e.g. Which region has the most Decline revenue? Where should we invest?")
    if q:
        st.session_state.chat.append({"role": "user", "content": q})
        st.chat_message("user").write(q)
        answer = None
        if key:
            system = (
                "You are the analytics assistant inside NovaRetail's customer dashboard, helping Sophia Martinez, Director of Customer Intelligence. "
                "Answer ONLY from the data summary below; quote exact figures, keep answers concise, and when asked for recommendations, tie them to the numbers. "
                "If the data cannot answer the question, say so. The sample is small, so flag low-confidence conclusions.\n\n" + build_context(df)
            )
            msgs = [{"role": "system", "content": system}] + st.session_state.chat[-8:]
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                                  headers={"Authorization": f"Bearer {key}"},
                                  json={"model": model, "messages": msgs, "temperature": 0.2, "max_tokens": 600}, timeout=30)
                r.raise_for_status()
                answer = r.json()["choices"][0]["message"]["content"]
            except Exception as e:
                answer = None
                st.warning(f"Groq call failed ({type(e).__name__}); using built-in answers instead.")
        if answer is None:
            answer = fallback_answer(q, df)
        st.session_state.chat.append({"role": "assistant", "content": answer})
        st.chat_message("assistant").write(answer)