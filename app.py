from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import json

PRIVATE = Path("data/private/categorized.csv")     # your real data, local only
SAMPLE = Path("data/sample/transactions.csv")      # synthetic demo data

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💸", layout="wide")

@st.cache_data
def load(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["weekday"] = df["date"].dt.day_name()
    return df

# ---------- sidebar: data source and filters ----------
st.sidebar.title("Filters")
sources = {}
if PRIVATE.exists():
    sources["My data (local only)"] = PRIVATE
if SAMPLE.exists():
    sources["Demo data (synthetic)"] = SAMPLE
if not sources:
    st.error("No data found. Run scripts/generate_fake_data.py first.")
    st.stop()

choice = st.sidebar.radio("Data source", list(sources))
df = load(sources[choice])
palette = px.colors.qualitative.Bold
CAT_COLORS = {c: palette[i % len(palette)] for i, c in enumerate(sorted(df["category"].unique()))}
CAT_COLORS["Person-to-Person"] = "#8A8F98"   # grey, so informative categories stand out

min_d, max_d = df["date"].min().date(), df["date"].max().date()
rng = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
if len(rng) != 2:
    st.info("Pick an end date.")
    st.stop()
start, end = rng

is_spend = (df["amount"] < 0) & (df["category"] != "Internal Transfer")
cats = sorted(df.loc[is_spend, "category"].unique())
picked = st.sidebar.multiselect("Categories", cats, default=cats)

hide_big = st.sidebar.checkbox("Hide one-off payments", value=True)
big = st.sidebar.slider("One-off means above (₹)", 5000, 200000, 20000, step=5000)

mask = (is_spend & df["category"].isin(picked)
        & df["date"].between(pd.Timestamp(start), pd.Timestamp(end)))
spend = df[mask].assign(spend=lambda d: -d["amount"])
if hide_big:
    spend = spend[spend["spend"] < big]
if spend.empty:
    st.warning("No transactions match these filters.")
    st.stop()

# ---------- header and KPIs ----------
st.title("💸 Personal Finance Tracker")
st.caption("Bank statement PDF → parsed → categorized (rules + ML) → analyzed")
if choice.startswith("Demo"):
    st.caption("Showing synthetic demo data, not real transactions.")

total = spend["spend"].sum()
days = (end - start).days + 1
by_cat = spend.groupby("category", as_index=False)["spend"].sum().sort_values("spend", ascending=False)
monthly = spend.groupby("month")["spend"].sum()

people = spend.loc[spend["category"] == "Person-to-Person", "spend"].sum()
shops = by_cat[by_cat["category"] != "Person-to-Person"]
top = shops.iloc[0] if not shops.empty else by_cat.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spent", f"₹{total:,.0f}")
c2.metric("Average per month", f"₹{total / days * 30.4:,.0f}")
c3.metric("Top category", top["category"].split(" &")[0],
          f"{top['spend'] / total:.0%} of spend", delta_color="off")
c4.metric("Sent to people", f"₹{people:,.0f}",
          f"{people / total:.0%} of spend", delta_color="off")

top_day = spend.groupby("weekday")["spend"].sum().idxmax()
st.markdown(
    f"**Insights:** your highest-spend month was **{monthly.idxmax():%b %Y}** "
    f"(₹{monthly.max():,.0f}); you spend the most on **{top_day}s**; "
    f"the typical payment is just **₹{spend['spend'].median():,.0f}**."
)

# ---------- tabs ----------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Categories", "Payees", "Transactions", "Model"])

with tab1:
    m = spend.groupby(["month", "category"], as_index=False)["spend"].sum()
    st.plotly_chart(px.bar(m, x="month", y="spend", color="category",
                           color_discrete_map=CAT_COLORS,
                           title="Monthly spending by category"))
    daily = spend.set_index("date")["spend"].resample("D").sum()
    roll = daily.rolling(7, min_periods=1).mean().reset_index()
    st.plotly_chart(px.line(roll, x="date", y="spend", title="Daily spending (7-day average)"))
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    wd = spend.groupby("weekday")["spend"].sum().reindex(order).fillna(0).reset_index()
    st.plotly_chart(px.bar(wd, x="weekday", y="spend", title="Spending by day of week"))

with tab2:
    left, right = st.columns(2)
    left.plotly_chart(px.pie(by_cat, names="category", values="spend", hole=0.55,
                              color="category", color_discrete_map=CAT_COLORS,
                             title="Share of spending"))
    tm = spend.groupby(["category", "payee_norm"], as_index=False)["spend"].sum()
    right.plotly_chart(px.treemap(tm, path=[px.Constant("All spending"), "category", "payee_norm"],
                                  values="spend", title="Where the money went"))

with tab3:
    top = (spend.groupby("payee_norm")
           .agg(spend=("spend", "sum"), txns=("spend", "size"))
           .sort_values("spend", ascending=False).head(15).reset_index())
    fig = px.bar(top, x="spend", y="payee_norm", orientation="h",
                 hover_data=["txns"], title="Top 15 payees")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig)

with tab4:
    q = st.text_input("Search payee")
    view = spend.sort_values("date", ascending=False)
    if q:
        view = view[view["payee_norm"].str.contains(q, case=False, na=False, regex=False)]
    show = view[["date", "payee_norm", "category", "spend"]].assign(date=lambda d: d["date"].dt.date)
    st.dataframe(show, hide_index=True)
    st.download_button("Download filtered CSV", show.to_csv(index=False),
                       "transactions.csv", "text/csv")

with tab5:
    st.subheader("Does ML help? An honest comparison")
    st.caption("Measured offline on the author's real bank statement: 689 labeled payments "
               "from 107 payees, tested on payees the model had never seen. "
               "The transactions in the other tabs are synthetic when Demo data is selected.")
    res = pd.DataFrame({
        "Task": ["Person vs merchant"] * 3 + ["Six categories"] * 3,
        "Method": ["Guess the common class", "One-line rule", "ML model",
                   "Guess the common class", "Keyword rules", "ML model"],
        "Accuracy": [72.7, 97.2, 98.1, 28.6, 36.0, 49.1],
    })
    fig = px.bar(res, x="Accuracy", y="Task", color="Method", barmode="group",
                 orientation="h", text="Accuracy", range_x=[0, 100])
    fig.update_traces(texttemplate="%{text:.1f}%")
    st.plotly_chart(fig)
    st.markdown(
        "**Telling people from shops is easy.** One rule (the payee has sent me money) "
        "gets 97.2%, and the ML model adds under a point.\n\n"
        "**Telling food from groceries from bills is hard.** With 107 payees, ML reaches "
        "49.1% against 36.0% for keyword rules, but that gain comes from separating people "
        "from shops. Among shop payments alone, the rules do better.\n\n"
        "**Why split by payee?** A random split scored 93.3%, because the model remembers "
        "names. Testing on unseen payees is the honest measure."
    )