import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LinearRegression
import numpy as np
import time

warnings.filterwarnings("ignore")

# ---- PAGE CONFIG ----
st.set_page_config(page_title="THANGALS Jewellery Dashboard", page_icon="💎", layout="wide")

# ---- USER AUTHENTICATION ----
USERS = {
    "basheer": {"password": "basheer123", "shops": ["Shamal"]},
    "raja": {"password": "raja123", "shops": ["Alras"]},
    "admin": {"password": "admin123", "shops": ["Alras", "Shamal"]}
}

# ---------- Helpers ----------
def style_card(label, value, sub=None, accent="#f6d365"):
    sub_html = f"<div style='font-size:0.85rem; opacity:0.75; margin-top:4px'>{sub}</div>" if sub else ""
    return f"""
    <div style="
        background: linear-gradient(135deg, {accent}, #fda085);
        padding:16px 18px; border-radius:18px; color:#222; box-shadow:0 10px 24px rgba(0,0,0,0.06);
        min-height:100px; display:flex; flex-direction:column; justify-content:center;">
        <div style="font-weight:600; font-size:0.95rem; opacity:0.8">{label}</div>
        <div style="font-size:1.8rem; font-weight:800; line-height:1.2; margin-top:6px">{value}</div>
        {sub_html}
    </div>
    """

def animate_kpi(container, label, target_value_float, sub=None, fmt="{:,.0f}", duration=0.8, steps=20):
    start = 0.0
    if steps <= 0: steps = 1
    delay = duration / steps
    for i in range(steps):
        val = start + (target_value_float - start) * ((i + 1) / steps)
        container.markdown(style_card(label, fmt.format(val), sub=sub), unsafe_allow_html=True)
        time.sleep(delay)

def pct_change(curr, prev):
    if prev == 0:
        return "—", "➖"  # no change
    change = ((curr - prev) / prev) * 100
    if change > 0:
        arrow = "📈"
    elif change < 0:
        arrow = "📉"
    else:
        arrow = "➖"
    return f"{arrow} {abs(change):.2f}%", arrow

def login_page():
    st.title("💎 THANGALS Jewellery Dashboard Login")
    st.markdown("Please enter your credentials to access the dashboard.")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            user_info = USERS.get(username)
            if user_info and user_info["password"] == password:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_shops'] = user_info["shops"]
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Incorrect username or password.")

def main_dashboard():
    # ---- PAGE TITLE & LOGOUT ----
    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.title(f"💎 THANGALS Jewellery Dashboard")
    with col_time:
        now = datetime.now()
        st.markdown(f"<h3 style='text-align: right; color: #fda085;'>{now.strftime('%A, %d %B %Y')}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: right; color: grey;'>{now.strftime('%I:%M:%S %p')}</h4>", unsafe_allow_html=True)

    username = st.session_state.get('username', 'User')
    st.sidebar.title(f"Welcome, {username.replace('_', ' ').title()}!")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('user_shops', None)
        st.rerun()

    st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)
    st_autorefresh(interval=30000, key="data_refresh")

    # ---- LOAD CSV ----
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    file_path = os.path.join(script_dir, "sales.csv")
    if not os.path.exists(file_path):
        st.error(f"❌ 'sales.csv' not found.")
        st.stop()
    try:
        df_full = pd.read_csv(file_path, encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"❌ Error reading CSV file: {e}")
        st.stop()

    # ---- FILTER DATA FOR LOGGED-IN USER ----
    user_shops = st.session_state.get('user_shops', [])
    df = df_full[df_full['Shop'].isin(user_shops)].copy()
    if df.empty:
        st.warning("⚠️ No data available for your assigned shop(s).")
        st.stop()

    # ---- DATA PREPROCESSING ----
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df.dropna(subset=["Date"], inplace=True)
    df["month_year"] = df["Date"].dt.to_period("M").dt.to_timestamp()

    # ---- SIDEBAR FILTERS ----
    st.sidebar.header("Filter Data")
    today = datetime.now().date()
    max_data_date = df["Date"].max().date()
    default_start_date = today if not df[df['Date'].dt.date == today].empty else max_data_date
    default_end_date = default_start_date
    from_date = st.sidebar.date_input("📅 From", default_start_date, min_value=df["Date"].min().date(), max_value=df["Date"].max().date())
    to_date = st.sidebar.date_input("📅 To", default_end_date, min_value=df["Date"].min().date(), max_value=df["Date"].max().date())
    locations = st.sidebar.multiselect("📍 Location", options=df["Location"].dropna().unique())
    shops = st.sidebar.multiselect("🏬 Shop", options=df["Shop"].dropna().unique(), default=user_shops)
    staffs = st.sidebar.multiselect("👤 Staff", options=df["Staff"].dropna().unique())
    categories = st.sidebar.multiselect("🗂 Category", options=df["Category"].dropna().unique())
    animate = st.sidebar.toggle("✨ Animate KPI cards", value=True)

    # ---- FILTER DATA LOGIC ----
    from_date_dt = pd.to_datetime(from_date)
    to_date_dt = pd.to_datetime(to_date)
    filtered_df = df[(df["Date"] >= from_date_dt) & (df["Date"] <= to_date_dt + timedelta(days=1))]
    if locations: filtered_df = filtered_df[filtered_df["Location"].isin(locations)]
    if shops: filtered_df = filtered_df[filtered_df["Shop"].isin(shops)]
    if staffs: filtered_df = filtered_df[filtered_df["Staff"].isin(staffs)]
    if categories: filtered_df = filtered_df[filtered_df["Category"].isin(categories)]
    if filtered_df.empty:
        st.warning("⚠️ No data available for the selected filters.")
        st.stop()

    # ---- KPI CALCULATIONS ----
    total_sales = float(filtered_df["Sales"].sum())
    total_profit = float(filtered_df["Profit"].sum())
    total_weight = float(filtered_df["Weight"].sum()) if "Weight" in filtered_df.columns else 0.0
    total_txn = len(filtered_df)

    # Previous period
    period_days = (to_date_dt - from_date_dt).days + 1
    prev_from_date = from_date_dt - timedelta(days=period_days)
    prev_to_date = to_date_dt - timedelta(days=period_days)
    prev_df = df[(df["Date"] >= prev_from_date) & (df["Date"] <= prev_to_date + timedelta(days=1))]
    if locations: prev_df = prev_df[prev_df["Location"].isin(locations)]
    if shops: prev_df = prev_df[prev_df["Shop"].isin(shops)]
    if staffs: prev_df = prev_df[prev_df["Staff"].isin(staffs)]
    if categories: prev_df = prev_df[prev_df["Category"].isin(categories)]

    prev_sales = float(prev_df["Sales"].sum()) if not prev_df.empty else 0.0
    prev_profit = float(prev_df["Profit"].sum()) if not prev_df.empty else 0.0
    prev_weight = float(prev_df["Weight"].sum()) if ("Weight" in prev_df.columns and not prev_df.empty) else 0.0
    prev_txn = len(prev_df)

    # ---- KPI CARDS ----
    st.markdown("###  Key Performance Indicators")
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        c = st.empty()
        pct, arrow = pct_change(total_sales, prev_sales)
        sub = f"{pct}"
        if animate: animate_kpi(c, "Total Sales", total_sales, sub=sub)
        else: c.markdown(style_card("Total Sales", f"{total_sales:,.0f}", sub=sub), unsafe_allow_html=True)

    with k2:
        c = st.empty()
        pct, arrow = pct_change(total_profit, prev_profit)
        sub = f"{pct}"
        if animate: animate_kpi(c, "Total Profit", total_profit, sub=sub)
        else: c.markdown(style_card("Total Profit", f"{total_profit:,.0f}", sub=sub), unsafe_allow_html=True)

    with k3:
        c = st.empty()
        pct, arrow = pct_change(total_weight, prev_weight)
        sub = f"{pct}"
        if animate: animate_kpi(c, "Total Weight (g)", total_weight, sub=sub, fmt="{:,.2f}")
        else: c.markdown(style_card("Total Weight (g)", f"{total_weight:,.2f}", sub=sub), unsafe_allow_html=True)

    with k4:
        c = st.empty()
        pct, arrow = pct_change(total_txn, prev_txn)
        sub = f"{pct}"
        if animate: animate_kpi(c, "Total Transactions", total_txn, sub=sub)
        else: c.markdown(style_card("Total Transactions", f"{total_txn:,}", sub=sub), unsafe_allow_html=True)

    # ---- TABS ----
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Category & Item", "🏬 Shop-wise", "🏆 Staff Performance", "📈 Time Analysis", "🔮 Sales Forecast"
    ])

    with tab1:
        st.subheader("Sales by Category & Item")
        category_df = filtered_df.groupby("Category", dropna=True).agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)
        item_df = filtered_df.groupby("Item", dropna=True).agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)

        left_col, right_col = st.columns(2)
        with left_col:
            fig_cat_bar = px.bar(category_df.head(10), x="Category", y="Sales", text_auto='.2s', title="Top Categories by Sales", color="Category")
            st.plotly_chart(fig_cat_bar, use_container_width=True)
        with right_col:
            fig_bar_item = px.bar(item_df.head(10), x="Sales", y="Item", orientation="h", text="Sales", title="Top Items by Sales")
            fig_bar_item.update_traces(texttemplate='AED %{text:,.2s}', textposition='outside')
            st.plotly_chart(fig_bar_item, use_container_width=True)

        st.dataframe(category_df, use_container_width=True)

    with tab2:
        st.subheader("Shop-wise Sales & Profit")
        shop_df = filtered_df.groupby("Shop").agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)

        # Combined chart: Sales (bar) + Profit (line)
        fig_shop = go.Figure()
        fig_shop.add_trace(go.Bar(x=shop_df["Shop"], y=shop_df["Sales"], name="Sales"))
        fig_shop.add_trace(go.Scatter(x=shop_df["Shop"], y=shop_df["Profit"], name="Profit", mode="lines+markers"))
        fig_shop.update_layout(title="Sales & Profit by Shop", yaxis_title="AED")
        st.plotly_chart(fig_shop, use_container_width=True)

        st.dataframe(shop_df, use_container_width=True)

    with tab3:
        st.subheader("Staff Performance")
        staff_df = filtered_df.groupby("Staff").agg(Sales=('Sales','sum'), Profit=('Profit','sum'), Transactions=('Date','count')).reset_index().sort_values("Sales", ascending=False)
        fig_staff = px.bar(staff_df, y="Staff", x="Sales", color="Profit", orientation='h', title="Sales by Staff Member", text='Sales')
        fig_staff.update_traces(texttemplate='AED %{text:,.2s}', textposition='outside')
        st.plotly_chart(fig_staff, use_container_width=True)
        st.dataframe(staff_df, use_container_width=True)

    with tab4:
        st.subheader("Daily Sales & Profit Trend (Selected Range)")
        daily_summary = filtered_df.groupby(pd.Grouper(key="Date", freq="D")).agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
        # Dual series line/area
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(x=daily_summary["Date"], y=daily_summary["Sales"], mode="lines+markers", name="Sales", fill="tozeroy"))
        fig_area.add_trace(go.Scatter(x=daily_summary["Date"], y=daily_summary["Profit"], mode="lines+markers", name="Profit"))
        fig_area.update_layout(title="Daily Sales vs Profit", xaxis_title="Date", yaxis_title="AED")
        st.plotly_chart(fig_area, use_container_width=True)
        st.dataframe(daily_summary, use_container_width=True)

    with tab5:
        st.subheader("Next Month Sales Forecast")
        forecast_df = df[df['Date'] <= to_date_dt].groupby("month_year")[["Sales"]].sum().reset_index()

        if len(forecast_df) > 1:
            X = np.arange(len(forecast_df)).reshape(-1, 1)
            y = forecast_df["Sales"].values
            model = LinearRegression().fit(X, y)
            predicted_sales = float(model.predict(np.array([[len(forecast_df)]]))[0])
            last_month_sales = float(y[-1])

            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=predicted_sales,
                title={'text': "Predicted Sales vs. Last Month"},
                delta={'reference': last_month_sales},
                gauge={'axis': {'range': [None, max(predicted_sales, last_month_sales) * 1.5]},
                       'bar': {'color': "#f6d365"}}
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            st.info("ℹ️ Not enough monthly data to generate a sales forecast.")

    # ---- AI ANALYZER ----
    st.markdown("## 🤖 AI Analyzer")
    with st.expander("Open analyzer"):
        # Build reference baselines from your own UAE market data in the CSV (same filters)
        # Recent monthly baseline: last 30 days (or up to dataset)
        lookback_days = 30
        end_ref = to_date_dt
        start_ref = max(df["Date"].min(), end_ref - timedelta(days=lookback_days - 1))
        ref_df = df[(df["Date"] >= start_ref) & (df["Date"] <= end_ref)]
        if locations: ref_df = ref_df[ref_df["Location"].isin(locations)]
        if shops: ref_df = ref_df[ref_df["Shop"].isin(shops)]
        if staffs: ref_df = ref_df[ref_df["Staff"].isin(staffs)]
        if categories: ref_df = ref_df[ref_df["Category"].isin(categories)]

        msg = []
        sel_len_days = (to_date_dt.date() - from_date_dt.date()).days + 1

        sel_sales = total_sales
        sel_profit = total_profit
        ref_daily = ref_df.groupby(pd.Grouper(key="Date", freq="D")).agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
        ref_daily_sales_mean = float(ref_daily["Sales"].mean()) if not ref_daily.empty else 0.0
        ref_daily_sales_median = float(ref_daily["Sales"].median()) if not ref_daily.empty else 0.0

        # Thresholds for "low"
        low_flag = False
        if sel_len_days == 1:
            # Compare single day to daily median
            low_flag = sel_sales < (0.85 * ref_daily_sales_median) if ref_daily_sales_median > 0 else False
        else:
            # Compare average per day over range
            sel_avg = sel_sales / sel_len_days
            low_flag = sel_avg < (0.85 * ref_daily_sales_median) if ref_daily_sales_median > 0 else False

        # Compose analysis
        msg.append(f"**Selected Range:** {from_date_dt.date()} → {to_date_dt.date()}  |  **Sales:** AED {sel_sales:,.0f}  |  **Profit:** AED {sel_profit:,.0f}  |  **Profit %:** {((sel_profit/sel_sales)*100 if sel_sales>0 else 0):.2f}%")
        if ref_daily_sales_median > 0:
            msg.append(f"**UAE Market Baseline (your last {lookback_days} days, same filters):** Median Daily Sales ≈ AED {ref_daily_sales_median:,.0f}, Mean ≈ AED {ref_daily_sales_mean:,.0f}")
        else:
            msg.append("_Not enough recent data to form a baseline; analyzer used current selection only._")

        if low_flag:
            msg.append("🔻 **Sales appear lower than your recent UAE market baseline.**")
            # Drill down suggestions
            # Shop
            shop_perf = filtered_df.groupby("Shop").agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)
            weak_shops = shop_perf[shop_perf["Sales"] == shop_perf["Sales"].min()]["Shop"].tolist() if not shop_perf.empty else []
            if weak_shops:
                msg.append(f"- Underperforming shop(s): **{', '.join(map(str, weak_shops))}**. Consider shifting inventory or boosting promotions here.")
            # Category
            cat_perf = filtered_df.groupby("Category").agg(Sales=('Sales','sum')).reset_index().sort_values("Sales")
            if not cat_perf.empty:
                bottom_cats = ", ".join(cat_perf.head(3)["Category"].astype(str).tolist())
                top_cats = ", ".join(cat_perf.tail(3)["Category"].astype(str).tolist())
                msg.append(f"- Categories to push: **{top_cats}**; watch low movers: **{bottom_cats}**.")
            # Staff
            staff_perf = filtered_df.groupby("Staff").agg(Sales=('Sales','sum'), Transactions=('Date','count')).reset_index().sort_values("Sales")
            if not staff_perf.empty:
                low_staff = ", ".join(staff_perf.head(2)["Staff"].astype(str).tolist())
                msg.append(f"- Coaching opportunity: **{low_staff}** based on sales/transactions.")
            # Timing
            if sel_len_days == 1 and previous_day_sales is not None:
                delta_vs_prev = sel_sales - previous_day_sales
                msg.append(f"- Change vs previous day: **AED {delta_vs_prev:,.0f}**. Plan a flash promo or outreach to repeat buyers.")
            msg.append("- Actions: refresh displays, add limited-time discounts on slow categories, promote high-margin diamond pieces during peak footfall, and retarget high-value customers from CRM.")
        else:
            msg.append("✅ **Sales are in line with or above your recent UAE market baseline.** Keep current merchandising and staff allocation; consider testing a premium upsell on top categories.")

        st.markdown("\n\n".join(msg))

    # ---- DOWNLOAD BUTTON ----
    st.sidebar.download_button(
        label="📥 Download Filtered Data",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_sales.csv',
        mime='text/csv'
    )

# --- MAIN APP ROUTER ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()
