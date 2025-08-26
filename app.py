import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
from streamlit_autorefresh import st_autorefresh

warnings.filterwarnings("ignore")

# ---- PAGE CONFIG ----
st.set_page_config(page_title="THANGALS Dashboard", page_icon="💎", layout="wide")
st.title("💎 THANGALS Business Dashboard")
st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

# ---- AUTO REFRESH EVERY 60 SECONDS ----
st_autorefresh(interval=60000, key="data_refresh")

# ---- LOAD CSV FUNCTION ----
@st.cache_data(ttl=60)  # refresh cache every 60 seconds
def load_data(file_path):
    return pd.read_csv(file_path, encoding="ISO-8859-1")

# ---- FILE PATH ----
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "sales.csv")

if not os.path.exists(file_path):
    st.error(f"❌ CSV file not found at: {file_path}")
    st.stop()

try:
    df = load_data(file_path)
except Exception as e:
    st.error(f"❌ Error reading CSV file: {e}")
    st.stop()

# ---- REFRESH BUTTON ----
if st.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.experimental_rerun()

# ---- REQUIRED COLUMNS ----
required_cols = ["Date","Location","Shop","Staff","Category","Sales","Weight","Cost","Profit"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
    st.stop()

# ---- DATA PREPROCESSING ----
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df.dropna(subset=["Date"], inplace=True)
df["month_year"] = df["Date"].dt.to_period("M").dt.to_timestamp()

# ---- SIDEBAR FILTERS ----
st.sidebar.header("Filter Data")
locations = st.sidebar.multiselect("📍 Location", options=df["Location"].dropna().unique())
shops = st.sidebar.multiselect("🏬 Shop", options=df["Shop"].dropna().unique())
staffs = st.sidebar.multiselect("👤 Staff", options=df["Staff"].dropna().unique())
categories = st.sidebar.multiselect("🗂 Category", options=df["Category"].dropna().unique())

# ---- AI SHOP SEARCH ----
st.sidebar.subheader("🔍 AI Shop Search")
ai_shop = st.sidebar.text_input("Type Shop Name:")
if ai_shop:
    shops = [s for s in df["Shop"].dropna().unique() if ai_shop.lower() in s.lower()]

# ---- DATE RANGE PICKER ----
st.sidebar.subheader("📅 Select Date Range")
from_date = st.sidebar.date_input("From", df["Date"].min())
to_date = st.sidebar.date_input("To", df["Date"].max())

# ---- FILTER DATA ----
filtered_df = df.copy()
if locations:
    filtered_df = filtered_df[filtered_df["Location"].isin(locations)]
if shops:
    filtered_df = filtered_df[filtered_df["Shop"].isin(shops)]
if staffs:
    filtered_df = filtered_df[filtered_df["Staff"].isin(staffs)]
if categories:
    filtered_df = filtered_df[filtered_df["Category"].isin(categories)]
filtered_df = filtered_df[(filtered_df["Date"] >= pd.to_datetime(from_date)) &
                          (filtered_df["Date"] <= pd.to_datetime(to_date))]

if filtered_df.empty:
    st.warning("⚠️ No data available for selected filters.")
    st.stop()

# ---- KPI CARDS ----
total_sales = filtered_df["Sales"].sum()
total_weight = filtered_df["Weight"].sum()
total_cost = filtered_df["Cost"].sum()
total_profit = filtered_df["Profit"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💰 Total Sales", f"${total_sales:,.2f}")
with col2:
    st.metric("⚖️ Total Weight", f"{total_weight:,.2f} g")
with col3:
    st.metric("🪙 Total Cost", f"${total_cost:,.2f}")
with col4:
    st.metric("📈 Total Profit", f"${total_profit:,.2f}")

# ---- MONTHLY SALES & PROFIT ----
monthly_summary = filtered_df.groupby("month_year").agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
monthly_summary["month_year_str"] = monthly_summary["month_year"].dt.strftime("%Y-%b")

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=monthly_summary["month_year_str"],
    y=monthly_summary["Sales"],
    mode="lines+markers",
    name="Sales",
    line=dict(color="gold", width=4),
    marker=dict(size=8)
))
fig_line.add_trace(go.Scatter(
    x=monthly_summary["month_year_str"],
    y=monthly_summary["Profit"],
    mode="lines+markers",
    name="Profit",
    line=dict(color="limegreen", width=4),
    marker=dict(size=8)
))
fig_line.update_layout(
    template="plotly_dark",
    title="📊 Monthly Sales vs Profit",
    xaxis_title="Month-Year",
    yaxis_title="Amount ($)",
    hovermode="x unified",
    height=450
)
st.plotly_chart(fig_line, use_container_width=True)

# ---- CATEGORY CHARTS ----
category_df = filtered_df.groupby("Category")["Sales"].sum().reset_index().sort_values("Sales", ascending=False)
top5_cat = category_df.head(5)

fig_pie = px.pie(
    top5_cat,
    names="Category",
    values="Sales",
    title="🟢 Top 5 Categories by Sales (Donut)",
    hole=0.4,
    color_discrete_sequence=px.colors.sequential.Viridis,
    template="plotly_dark"
)
fig_pie.update_traces(textinfo="label+percent")
st.plotly_chart(fig_pie, use_container_width=True)

fig_bar_cat = px.bar(
    category_df[::-1],
    x="Sales",
    y="Category",
    orientation="h",
    text="Sales",
    color="Sales",
    color_continuous_scale="Viridis",
    template="plotly_dark",
    title="🟢 Sales by Category (All)"
)
fig_bar_cat.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
st.plotly_chart(fig_bar_cat, use_container_width=True)

# ---- TOP 5 STAFF ----
top_staff = filtered_df.groupby("Staff")["Sales"].sum().sort_values(ascending=False).head(5).reset_index()
fig_staff = px.bar(
    top_staff, x="Staff", y="Sales", text="Sales", color="Sales",
    title="🏆 Top 5 Staff by Sales", template="plotly_dark", color_continuous_scale="Viridis"
)
fig_staff.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
st.plotly_chart(fig_staff, use_container_width=True)

# ---- SHOP-WISE SALES & PROFIT ----
shop_df = filtered_df.groupby("Shop")[["Sales","Profit"]].sum().reset_index()
fig_shop = px.bar(
    shop_df,
    x="Shop",
    y=["Sales","Profit"],
    barmode="group",
    text_auto=".2f",
    color_discrete_sequence=["#1f77b4", "#ff7f0e"],
    title="🏬 Shop-wise Sales & Profit",
    template="plotly_dark"
)
st.plotly_chart(fig_shop, use_container_width=True)

# ---- DOWNLOAD BUTTON ----
csv = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Filtered Data",
    data=csv,
    file_name="filtered_sales.csv",
    mime="text/csv"
)
