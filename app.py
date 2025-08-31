import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
from datetime import datetime, timedelta, time
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LinearRegression
import numpy as np
import time as time_module  # Using alias to prevent name conflict
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

warnings.filterwarnings("ignore")

# ---- PAGE CONFIG ----
st.set_page_config(
    page_title="THANGALS Jewellery Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---- CUSTOM CSS ----
st.markdown("""
<style>
.block-container {padding:1rem 2rem;}
/* You can add more custom styles here if needed */
</style>
""", unsafe_allow_html=True)

# ---- USER AUTHENTICATION ----
USERS = {
    "basheer": {"password": "basheer123", "shops": ["Shamal"]},
    "raja": {"password": "raja123", "shops": ["Alras"]},
    "admin": {"password": "admin123", "shops": ["Alras", "Shamal"]}
}

# --- EMAIL CONFIG (IMPORTANT: Replace with your actual credentials) ---
SENDER_EMAIL = "nabdulhaq5@gmail.com"
SENDER_PASSWORD = "Abdulhaq@8117"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# Pre-defined list of managers' emails for the scheduler
MANAGER_EMAILS = {
    "General Manager": "gm@example.com",
    "Sales Head": "sales.head@example.com",
    "Admin": "nabdulhaq5@gmail.com"
}

# ---------- Helper Functions ----------
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
        time_module.sleep(delay)

def pct_change(curr, prev):
    if prev == 0:
        return "—", "➖"
    change = ((curr - prev) / prev) * 100
    arrow = "📈" if change > 0 else "📉" if change < 0 else "➖"
    return f"{arrow} {abs(change):.2f}%", arrow

def get_seasonal_context(selected_date):
    month = selected_date.month
    context = {
        1: "Winter peak tourist season, Dubai Shopping Festival. High footfall from international visitors.",
        2: "Cooler weather, Valentine's Day. Good for couple-themed promotions.",
        3: "Transition to warmer weather. Potential for pre-Ramadan shopping.",
        4: "Often coincides with Ramadan. Sales may shift to evening hours. Focus on traditional items for Eid.",
        5: "Often coincides with Eid Al Fitr, a major gift-giving period.",
        6: "Hot summer begins. Lower tourist footfall. Focus on local promotions.",
        7: "Hottest month. Traditionally a slower retail period.",
        8: "Summer sales. Onam can drive sales in specific demographics.",
        9: "Weather cools. Raksha Bandhan & North Indian festival season can drive demand.",
        10: "Often coincides with Diwali, a peak season for gold sales among Indian expatriates.",
        11: "Winter season returns. Tourists are back. Pre-Christmas shopping.",
        12: "Christmas and New Year's Eve. High tourist numbers. Strong demand for gifts."
    }
    return context.get(month, "No specific seasonal factor identified for this month.")

def generate_analysis_text(analysis_type, **kwargs):
    """Generates tailored AI analysis text based on the selected tab."""
    from_date = kwargs.get('from_date')
    to_date = kwargs.get('to_date')
    analysis_text = [f"**Analysis for: {from_date.strftime('%d-%b-%Y')} to {to_date.strftime('%d-%b-%Y')}**\n"]

    if analysis_type == "Overall":
        total_sales, total_profit, total_txn, total_weight = kwargs.get('kpis')
        profit_margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
        avg_txn = total_sales / total_txn if total_txn > 0 else 0
        sales_per_gram = total_sales / total_weight if total_weight > 0 else 0
        analysis_text.append(f"#### 📈 Overall Business Health:")
        analysis_text.append(f"- **Total Sales:** AED {total_sales:,.0f} from {total_txn} transactions.")
        analysis_text.append(f"- **Profitability:** The overall profit margin is **{profit_margin:.2f}%**. A healthy margin for jewellery retail is typically 20-40%; assess your performance against this benchmark.")
        analysis_text.append(f"- **Efficiency:** You are averaging **AED {avg_txn:,.0f} per transaction** and generating **AED {sales_per_gram:,.0f} for every gram** of material sold.")
        analysis_text.append(f"- **Recommendation:** To improve overall health, focus on increasing the average transaction value by upselling or cross-selling items. Promoting high-margin categories (like diamonds) can also significantly boost profitability.")

    elif analysis_type == "Category":
        category_df, item_df = kwargs.get('data')
        analysis_text.append(f"#### 📊 Category & Item Insights:")
        if not category_df.empty:
            top_cat = category_df.iloc[0]
            analysis_text.append(f"- **Top Category:** '{top_cat['Category']}' is the strongest performer, contributing **AED {top_cat['Sales']:,.0f}** in sales.")
            if len(category_df) > 1:
                bottom_cat = category_df.iloc[-1]
                analysis_text.append(f"- **Area for Improvement:** '{bottom_cat['Category']}' is the weakest category with **AED {bottom_cat['Sales']:,.0f}** in sales. Consider a targeted promotion or stock review.")
        if not item_df.empty:
            analysis_text.append(f"- **Best Seller:** The top-selling item is '{item_df.iloc[0]['Item']}'. Ensure this is always well-stocked and prominently displayed.")
        analysis_text.append(f"- **Recommendation:** Create bundles with top-selling items and weaker, high-margin products. Use the top category's success as a template for marketing other categories.")

    elif analysis_type == "Shop":
        shop_df = kwargs.get('data')
        analysis_text.append(f"#### 🏬 Shop Performance Insights:")
        if not shop_df.empty and len(shop_df) > 0:
            top_shop = shop_df.iloc[0]
            analysis_text.append(f"- **Top Performer:** '{top_shop['Shop']}' leads with **AED {top_shop['Sales']:,.0f}** in sales and a profit of **AED {top_shop['Profit']:,.0f}**.")
            if len(shop_df) > 1:
                bottom_shop = shop_df.iloc[-1]
                analysis_text.append(f"- **Underperformer:** '{bottom_shop['Shop']}' is lagging with **AED {bottom_shop['Sales']:,.0f}** in sales. This could be due to location, inventory mix, or staff performance.")
            analysis_text.append(f"- **Recommendation:** Analyze what makes '{top_shop['Shop']}' successful—is it their inventory, staff, or location? Apply these learnings to '{bottom_shop['Shop']}'. Consider moving high-performing staff or popular items to the underperforming shop temporarily.")
        else:
            analysis_text.append("- No shop-level data to analyze with current filters.")

    elif analysis_type == "Staff":
        staff_df = kwargs.get('data')
        analysis_text.append(f"#### 🏆 Staff Performance Insights:")
        if not staff_df.empty:
            top_staff_sales = staff_df.iloc[0]
            top_staff_txn = staff_df.sort_values("Transactions", ascending=False).iloc[0]
            analysis_text.append(f"- **Top Salesperson:** '{top_staff_sales['Staff']}' generated the most revenue (**AED {top_staff_sales['Sales']:,.0f}**). This indicates strong upselling skills.")
            analysis_text.append(f"- **Most Active:** '{top_staff_txn['Staff']}' handled the highest number of transactions ({top_staff_txn['Transactions']}). This shows efficiency and good customer engagement.")
            analysis_text.append(f"- **Recommendation:** Pair top salespeople with others for mentoring. Recognize '{top_staff_txn['Staff']}' for their high activity. For staff with low sales and transactions, offer targeted training on product knowledge and sales techniques.")
        else:
            analysis_text.append("- No staff-level data to analyze with current filters.")
    
    elif analysis_type == "Time":
        daily_summary = kwargs.get('data')
        analysis_text.append(f"#### 📈 Time & Seasonality Insights:")
        if not daily_summary.empty:
            peak_day = daily_summary.loc[daily_summary['Sales'].idxmax()]
            analysis_text.append(f"- **Peak Day:** The best sales day in this period was **{peak_day['Date'].strftime('%A, %d-%b')}** with **AED {peak_day['Sales']:,.0f}**.")
        analysis_text.append(f"- **Seasonal Context:** This period falls within: *{get_seasonal_context(from_date)}*")
        analysis_text.append(f"- **Recommendation:** Align your marketing and promotions with the seasonal context. For example, during tourist season, focus on high-ticket items. During festival periods like Diwali or Onam, promote traditional gold jewellery. Use insights from peak sales days to plan future staffing and inventory.")

    elif analysis_type == "Forecast":
        predicted_sales, last_month_sales = kwargs.get('data')
        change = ((predicted_sales - last_month_sales) / last_month_sales) * 100 if last_month_sales > 0 else 0
        change_text = f"an increase of {change:.2f}%" if change > 0 else f"a decrease of {abs(change):.2f}%"
        analysis_text.append(f"#### 🔮 Sales Forecast Insights:")
        analysis_text.append(f"- **Prediction:** The linear forecast for next month is **AED {predicted_sales:,.0f}**, which is **{change_text}** compared to the last recorded month's sales of AED {last_month_sales:,.0f}.")
        analysis_text.append(f"- **Context:** This is a simple trend-based forecast. The actual performance will be influenced by upcoming events: *{get_seasonal_context(datetime.now() + timedelta(days=30))}*")
        analysis_text.append(f"- **Recommendation:** To meet or exceed this forecast, plan promotions aligned with the upcoming seasonal context. If a decrease is predicted, consider a marketing campaign to boost sales.")

    return "\n".join(analysis_text)


# ---------- Email Functions ----------
def generate_daily_report_html(df_full, shop_list):
    today = datetime.now().date()
    today_df = df_full[df_full['Date'].dt.date == today].copy()

    if shop_list:
        today_df = today_df[today_df['Shop'].isin(shop_list)]

    if today_df.empty:
        return f"<h3>No sales recorded today ({today.strftime('%d %B %Y')}) for the selected shops.</h3>"

    total_sales = today_df['Sales'].sum()
    total_profit = today_df['Profit'].sum()
    total_weight = today_df['Weight'].sum() if 'Weight' in today_df.columns else 0
    total_txns = len(today_df)

    top_items = today_df.groupby('Item')['Sales'].sum().nlargest(5).reset_index()
    top_items_html = top_items.to_html(index=False, float_format='{:,.0f}'.format) if not top_items.empty else "<p>No item sales to display.</p>"

    html = f"""
    <html><body>
        <h2>Thangals Jewellery Daily Sales Report: {today.strftime('%d %B %Y')}</h2>
        <p>This is an automated daily sales summary.</p>
        <h3>Key Metrics for Today:</h3>
        <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td><b>Total Sales</b></td><td>AED {total_sales:,.2f}</td></tr>
            <tr><td><b>Total Profit</b></td><td>AED {total_profit:,.2f}</td></tr>
            <tr><td><b>Total Weight Sold</b></td><td>{total_weight:,.2f} g</td></tr>
            <tr><td><b>Total Transactions</b></td><td>{total_txns}</td></tr>
        </table>
        <h3>Top 5 Selling Items Today:</h3>
        {top_items_html}
        <br><p><i>Report generated by Thangals BI Dashboard.</i></p>
    </body></html>
    """
    return html

def send_email(recipients, subject, html_content):
    if not SENDER_EMAIL or SENDER_EMAIL == "your_email@example.com":
        st.sidebar.error("Email not configured. Update credentials in the script.")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Thangals Dashboard <{SENDER_EMAIL}>"
    message["To"] = ", ".join(recipients)
    message.attach(MIMEText(html_content, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipients, message.as_string())
        st.sidebar.success(f"Report sent to {len(recipients)} manager(s)!")
    except Exception as e:
        st.sidebar.error(f"Failed to send email: {e}")


# ---------- Minimal data cleaning (NO category mapping) ----------
def clean_and_fix_categories(df: pd.DataFrame) -> pd.DataFrame:
    """
    This function only ensures required columns exist and numeric conversions.
    It does NOT change or infer Category values — Category is used exactly as present in the Excel.
    """
    expected_cols = ["Date", "Shop", "Location", "Staff", "Item", "Category", "Weight", "Sales", "Profit"]
    for c in expected_cols:
        if c not in df.columns:
            if c == "Date":
                df[c] = pd.NaT
            elif c in ["Weight", "Sales", "Profit"]:
                df[c] = 0
            else:
                df[c] = ""

    # Convert numeric columns safely
    for numcol in ["Weight", "Sales", "Profit"]:
        df[numcol] = pd.to_numeric(df[numcol], errors="coerce").fillna(0)

    # Trim whitespace from Item and Category but do not remap
    df["Item"] = df["Item"].astype(str).str.strip()
    df["Category"] = df["Category"].astype(str).str.strip()

    return df


# ---------- AUTHENTICATION & MAIN APP ----------
def login_page():
    st.title("💎 THANGALS Jewellery Dashboard Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            user_info = USERS.get(username)
            if user_info and user_info["password"] == password:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_shops'] = user_info["shops"]
                st.rerun()
            else:
                st.error("Incorrect username or password.")

def main_dashboard():
    # ---- HEADER ----
    col_title, col_time = st.columns([3, 1])
    with col_title:
        st.title("💎 THANGALS Jewellery Dashboard")
    with col_time:
        now = datetime.now()
        st.markdown(f"<h3 style='text-align:right;color:#fda085;'>{now.strftime('%A, %d %B %Y')}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align:right;color:grey;'>{now.strftime('%I:%M:%S %p')}</h4>", unsafe_allow_html=True)

    st_autorefresh(interval=60000, key="data_refresh")

    # ---- LOAD DATA ----
    try:
        file_path = "sales.csv"
        if not os.path.exists(file_path):
            st.error("❌ 'sales.csv' not found.")
            st.stop()
        df_full = pd.read_csv(file_path, encoding="ISO-8859-1")
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.stop()

    # Dates
    df_full["Date"] = pd.to_datetime(df_full["Date"], errors="coerce")
    df_full.dropna(subset=["Date"], inplace=True)
    df_full["month_year"] = df_full["Date"].dt.to_period("M").dt.to_timestamp()

    # Minimal cleaning (no mapping)
    df_full = clean_and_fix_categories(df_full)

    # ---- SIDEBAR ----
    username = st.session_state.get('username', 'User')
    st.sidebar.title(f"Welcome, {username.replace('_',' ').title()}!")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    st.sidebar.header("Filter Options")
    
    # User permission scope (keep permission logic)
    user_shops_permission = st.session_state.get('user_shops', [])
    df = df_full[df_full['Shop'].isin(user_shops_permission)].copy()
    if df.empty:
        st.warning("⚠️ No data available for your assigned shop(s).")
        st.stop()

    # Date filters
    today = datetime.now().date()
    default_start_date = today if not df[df['Date'].dt.date == today].empty else df["Date"].max().date()
    from_date = st.sidebar.date_input("📅 From", default_start_date, min_value=df["Date"].min().date(), max_value=df["Date"].max().date())
    to_date = st.sidebar.date_input("📅 To", default_start_date, min_value=df["Date"].min().date(), max_value=df["Date"].max().date())

    # --- FIXED "SELECT ALL SHOPS" LOGIC ---
    # Build shop options from the permission-scoped df (shows only shops the user is allowed to see)
    all_shops_option = sorted(df["Shop"].dropna().unique().tolist())
    select_all_shops = st.sidebar.checkbox("Select All Shops", value=True)
    if select_all_shops:
        default_selection = all_shops_option
    else:
        default_selection = user_shops_permission

    selected_shops = st.sidebar.multiselect(
        "🏬 Shop",
        options=all_shops_option,
        default=default_selection
    )
    
    # Other filters (Category uses exactly the values from Excel)
    locations = st.sidebar.multiselect("📍 Location", options=sorted(df["Location"].dropna().unique()))
    staffs = st.sidebar.multiselect("👤 Staff", options=sorted(df["Staff"].dropna().unique()))
    categories = st.sidebar.multiselect("🗂 Category", options=sorted(df["Category"].dropna().unique()))
    animate = st.sidebar.toggle("✨ Animate KPI cards", value=True)

    # ---- FILTERING LOGIC ----
    from_date_dt = pd.to_datetime(from_date)
    to_date_dt = pd.to_datetime(to_date)

    filtered_df = df[(df["Date"] >= from_date_dt) & (df["Date"] <= to_date_dt + timedelta(days=1))]
    if selected_shops: filtered_df = filtered_df[filtered_df["Shop"].isin(selected_shops)]
    if locations: filtered_df = filtered_df[filtered_df["Location"].isin(locations)]
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

    # Previous period comparison
    period_days = (to_date_dt.date() - from_date_dt.date()).days + 1
    prev_from_date = from_date_dt - timedelta(days=period_days)
    prev_df_base = df[(df["Date"] >= prev_from_date) & (df["Date"] < from_date_dt)]
    if selected_shops: prev_df_base = prev_df_base[prev_df_base["Shop"].isin(selected_shops)]
    if locations: prev_df_base = prev_df_base[prev_df_base["Location"].isin(locations)]
    
    prev_sales = float(prev_df_base["Sales"].sum())
    prev_profit = float(prev_df_base["Profit"].sum())
    prev_weight = float(prev_df_base["Weight"].sum()) if "Weight" in prev_df_base.columns else 0.0
    prev_txn = len(prev_df_base)

    # ---- KPI DISPLAY ----
    st.markdown("### Key Performance Indicators")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        c = st.empty()
        pct, _ = pct_change(total_sales, prev_sales)
        if animate: animate_kpi(c, "Total Sales", total_sales, sub=f"{pct} vs prev. period")
        else: c.markdown(style_card("Total Sales", f"{total_sales:,.0f}", sub=f"{pct} vs prev. period"), unsafe_allow_html=True)
    with k2:
        c = st.empty()
        pct, _ = pct_change(total_profit, prev_profit)
        if animate: animate_kpi(c, "Total Profit", total_profit, sub=f"{pct} vs prev. period")
        else: c.markdown(style_card("Total Profit", f"{total_profit:,.0f}", sub=f"{pct} vs prev. period"), unsafe_allow_html=True)
    with k3:
        c = st.empty()
        pct, _ = pct_change(total_weight, prev_weight)
        if animate: animate_kpi(c, "Total Weight (g)", total_weight, sub=f"{pct} vs prev. period", fmt="{:,.2f}")
        else: c.markdown(style_card("Total Weight (g)", f"{total_weight:,.2f}", sub=f"{pct} vs prev. period"), unsafe_allow_html=True)
    with k4:
        c = st.empty()
        pct, _ = pct_change(total_txn, prev_txn)
        if animate: animate_kpi(c, "Total Transactions", total_txn, sub=f"{pct} vs prev. period")
        else: c.markdown(style_card("Total Transactions", f"{total_txn:,}", sub=f"{pct} vs prev. period"), unsafe_allow_html=True)
        
    st.markdown("<hr>", unsafe_allow_html=True)

    # ---- VISUALIZATION TABS WITH INTEGRATED AI ANALYZER ----
    tab_list = [
        "📈 Overall Business Health",
        "📊 Category & Item",
        "🏬 Shop-wise",
        "🏆 Staff Performance",
        "📈 Time Analysis",
        "🔮 Sales Forecast"
    ]
    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_list)

    with tab0:
        st.subheader("Overall Business Health Metrics")
        m1, m2, m3 = st.columns(3)
        profit_margin = (total_profit / total_sales) * 100 if total_sales > 0 else 0
        avg_txn_value = total_sales / total_txn if total_txn > 0 else 0
        sales_per_gram = total_sales / total_weight if total_weight > 0 else 0
        m1.metric(label="Overall Profit Margin", value=f"{profit_margin:.2f}%")
        m2.metric(label="Average Transaction Value", value=f"AED {avg_txn_value:,.2f}")
        m3.metric(label="Average Sales per Gram", value=f"AED {sales_per_gram:,.2f}")
        
        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            analysis = generate_analysis_text("Overall", kpis=(total_sales, total_profit, total_txn, total_weight), from_date=from_date, to_date=to_date)
            st.info(analysis)

    with tab1:
        st.subheader("Sales by Category & Item")
        category_df = filtered_df.groupby("Category").agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)
        item_df = filtered_df.groupby("Item").agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)
        c1, c2 = st.columns(2)
        fig_cat_bar = px.bar(category_df.head(10), x="Category", y="Sales", text_auto='.2s', title="Top 10 Categories by Sales", color="Category")
        c1.plotly_chart(fig_cat_bar, use_container_width=True)
        fig_bar_item = px.bar(item_df.head(10), x="Sales", y="Item", orientation="h", text="Sales", title="Top 10 Items by Sales")
        fig_bar_item.update_traces(texttemplate='AED %{text:,.2s}', textposition='outside')
        c2.plotly_chart(fig_bar_item, use_container_width=True)

        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            analysis = generate_analysis_text("Category", data=(category_df, item_df), from_date=from_date, to_date=to_date)
            st.info(analysis)

    with tab2:
        st.subheader("Shop-wise Sales & Profit")
        shop_df = filtered_df.groupby("Shop").agg(Sales=('Sales','sum'), Profit=('Profit','sum')).reset_index().sort_values("Sales", ascending=False)
        fig_shop = go.Figure()
        fig_shop.add_trace(go.Bar(x=shop_df["Shop"], y=shop_df["Sales"], name="Sales", marker_color='#f6d365'))
        fig_shop.add_trace(go.Scatter(x=shop_df["Shop"], y=shop_df["Profit"], name="Profit", mode="lines+markers", line=dict(color='#fda085')))
        fig_shop.update_layout(title="Sales & Profit by Shop", yaxis_title="AED")
        st.plotly_chart(fig_shop, use_container_width=True)

        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            analysis = generate_analysis_text("Shop", data=shop_df, from_date=from_date, to_date=to_date)
            st.info(analysis)

    with tab3:
        st.subheader("Staff Performance")
        staff_df = filtered_df.groupby("Staff").agg(Sales=('Sales','sum'), Profit=('Profit','sum'), Transactions=('Date','count')).reset_index().sort_values("Sales", ascending=False)
        fig_staff = px.bar(staff_df.head(10), y="Staff", x="Sales", color="Profit", orientation='h', title="Top 10 Staff by Sales", text='Sales', color_continuous_scale=px.colors.sequential.Viridis)
        fig_staff.update_traces(texttemplate='AED %{text:,.2s}', textposition='outside')
        st.plotly_chart(fig_staff, use_container_width=True)
        
        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            analysis = generate_analysis_text("Staff", data=staff_df, from_date=from_date, to_date=to_date)
            st.info(analysis)

    with tab4:
        st.subheader("Daily Sales & Profit Trend")
        daily_summary = filtered_df.groupby(pd.Grouper(key="Date", freq="D")).agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(x=daily_summary["Date"], y=daily_summary["Sales"], mode="lines+markers", name="Sales", fill="tozeroy", line=dict(color='#f6d365')))
        fig_area.add_trace(go.Scatter(x=daily_summary["Date"], y=daily_summary["Profit"], mode="lines+markers", name="Profit", line=dict(color='#fda085')))
        fig_area.update_layout(title="Daily Sales vs Profit", xaxis_title="Date", yaxis_title="AED")
        st.plotly_chart(fig_area, use_container_width=True)

        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            analysis = generate_analysis_text("Time", data=daily_summary, from_date=from_date, to_date=to_date)
            st.info(analysis)

    with tab5:
        st.subheader("Next Month Sales Forecast (Linear Trend)")
        forecast_df = df[df['Date'] <= to_date_dt].groupby("month_year")[["Sales"]].sum().reset_index()
        predicted_sales, last_month_sales = 0, 0
        if len(forecast_df) > 2:
            X = np.arange(len(forecast_df)).reshape(-1, 1)
            y = forecast_df["Sales"].values
            model = LinearRegression().fit(X, y)
            predicted_sales = float(model.predict(np.array([[len(forecast_df)]]))[0])
            last_month_sales = float(y[-1])
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=predicted_sales,
                title={'text': "Predicted Sales vs. Last Month"},
                delta={'reference': last_month_sales, 'increasing': {'color': "#3AD594"}, 'decreasing': {'color': "#FF5B5B"}},
                gauge={'axis': {'range': [None, max(predicted_sales, last_month_sales) * 1.5]}, 'bar': {'color': "#f6d365"}}
            ))
            st.plotly_chart(fig_gauge, use_container_width=True)
        else:
            st.info("ℹ️ At least 3 months of data are needed to generate a basic forecast.")
        
        st.markdown("---")
        with st.expander("🤖 Show AI Analysis & Recommendations"):
            if predicted_sales > 0:
                analysis = generate_analysis_text("Forecast", data=(predicted_sales, last_month_sales), from_date=from_date, to_date=to_date)
                st.info(analysis)
            else:
                st.warning("Not enough data to generate analysis.")

    # ---- AUTOMATION & DOWNLOAD ----
    st.sidebar.title("Automation & Data")
    
    # Email Scheduler
    st.sidebar.subheader("📧 Daily Report Automation")
    selected_managers = st.sidebar.multiselect("Select Managers", options=list(MANAGER_EMAILS.keys()))
    schedule_time_obj = st.sidebar.time_input("Send report daily at (24h):", value=time(22, 0))

    if st.sidebar.button("Schedule/Update Daily Report"):
        if selected_managers:
            st.session_state['schedule_time'] = schedule_time_obj
            st.session_state['recipients'] = [MANAGER_EMAILS[name] for name in selected_managers]
            st.session_state['last_sent_date'] = None
            st.sidebar.success(f"Report scheduled for {schedule_time_obj} to {len(selected_managers)} manager(s).")
        else:
            st.sidebar.warning("Please select at least one manager.")
            
    # Download button
    st.sidebar.download_button(
        label="📥 Download Filtered Data",
        data=filtered_df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_sales_data.csv',
        mime='text/csv'
    )

    # --- Background logic to check schedule and send email ---
    if 'schedule_time' in st.session_state and 'recipients' in st.session_state:
        now = datetime.now()
        if now.time() >= st.session_state['schedule_time'] and st.session_state.get('last_sent_date') != now.date():
            with st.spinner("Sending daily report..."):
                report_html = generate_daily_report_html(df_full, user_shops_permission)
                send_email(st.session_state['recipients'], f"Thangals Daily Sales Report - {now.strftime('%d %B %Y')}", report_html)
                st.session_state['last_sent_date'] = now.date()

# --- MAIN APP ROUTER ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()
