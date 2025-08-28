import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import warnings
import os
import time
from streamlit_autorefresh import st_autorefresh
from sklearn.linear_model import LinearRegression
import numpy as np

warnings.filterwarnings("ignore")

# ---- PAGE CONFIG ----
st.set_page_config(page_title="THANGALS Jewellery Dashboard", page_icon="💎", layout="wide")

# ---- USER AUTHENTICATION ----
# Usernames and shops updated as per your file
USERS = {
    "basheer": {
        "password": "basheer123",
        "shops": ["Shamal"]
    },
    "raja": {
        "password": "raja123",
        "shops": ["Alras"]
    },
    "admin": {
        "password": "admin123",
        "shops": ["Alras", "Shamal"]
    }
}

# --- LOGIN FUNCTION ---
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

# --- MAIN DASHBOARD FUNCTION ---
def main_dashboard():
    # ---- PAGE TITLE & LOGOUT ----
    st.title(f"💎 THANGALS Jewellery Dashboard")
    username = st.session_state.get('username', 'User')
    st.sidebar.title(f"Welcome, {username.replace('_', ' ').title()}!")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state.pop('username', None)
        st.session_state.pop('user_shops', None)
        st.rerun()

    st.markdown('<style>div.block-container{padding-top:2rem;}</style>', unsafe_allow_html=True)

    # ---- BACKGROUND MUSIC ----
    st.markdown("""
    <audio autoplay loop>
      <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
    </audio>
    """, unsafe_allow_html=True)

    # ---- AUTO REFRESH ----
    st_autorefresh(interval=80000, key="data_refresh")

    # ---- LOAD CSV FUNCTION ----
    @st.cache_data
    def load_data(file_path):
        return pd.read_csv(file_path, encoding="ISO-8859-1")

    # ---- FILE PATH & DATA LOADING ----
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "sales.csv")

    if not os.path.exists(file_path):
        st.error(f"❌ CSV file not found at: {file_path}")
        st.stop()

    try:
        df_full = load_data(file_path)
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
    locations = st.sidebar.multiselect("📍 Location", options=df["Location"].dropna().unique())
    shops = st.sidebar.multiselect("🏬 Shop", options=df["Shop"].dropna().unique())
    staffs = st.sidebar.multiselect("👤 Staff", options=df["Staff"].dropna().unique())
    categories = st.sidebar.multiselect("🗂 Category", options=df["Category"].dropna().unique())
    items = st.sidebar.multiselect("💎 Item", options=df["Item"].dropna().unique())
    from_date = st.sidebar.date_input("📅 From", df["Date"].min())
    to_date = st.sidebar.date_input("📅 To", df["Date"].max())

    # ---- FILTER DATA LOGIC ----
    filtered_df = df.copy()
    if locations:
        filtered_df = filtered_df[filtered_df["Location"].isin(locations)]
    if shops:
        filtered_df = filtered_df[filtered_df["Shop"].isin(shops)]
    if staffs:
        filtered_df = filtered_df[filtered_df["Staff"].isin(staffs)]
    if categories:
        filtered_df = filtered_df[filtered_df["Category"].isin(categories)]
    if items:
        filtered_df = filtered_df[filtered_df["Item"].isin(items)]
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
    num_transactions = len(filtered_df)
    avg_sale = total_sales / num_transactions if num_transactions > 0 else 0

    def kpi_card(value, label, emoji, unit=""):
        st.markdown(
            f"""
            <div style='padding:15px; text-align:center; background:linear-gradient(90deg, #f6d365, #fda085); border-radius:15px; height: 100%;'>
                <h3>{emoji} {label}</h3>
                <h2>{unit}{value:,.2f}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    ## KPI cards arranged in two balanced rows of three
    col1, col2, col3 = st.columns(3)
    with col1: kpi_card(total_sales, "Total Sales", "💰", "AED ")
    with col2: kpi_card(total_profit, "Total Profit", "📈", "AED ")
    with col3: kpi_card(total_weight, "Total Weight (g)", "⚖️")

    st.markdown("<br>", unsafe_allow_html=True) 

    col4, col5, col6 = st.columns(3)
    with col4: kpi_card(num_transactions, "Transactions", "🧾")
    with col5: kpi_card(avg_sale, "Avg Sale Value", "💵", "AED ")
    with col6: kpi_card(total_cost, "Total Cost", "🪙", "AED ")


    # ---- CATEGORY & ITEM ANALYSIS ----
    st.subheader("📊 Sales by Category & Item")
    
    category_df = filtered_df.groupby("Category").agg(
        Sales=('Sales','sum'),
        Weight=('Weight','sum'),
        Profit=('Profit','sum')
    ).reset_index().sort_values("Sales", ascending=False)
    
    ## Sales by Category changed to a BAR CHART
    fig_cat_bar = px.bar(category_df.head(5), x="Category", y="Sales",
                         text_auto='.2s', title="Top 5 Categories by Sales",
                         color="Category", template="plotly_white")
    fig_cat_bar.update_traces(textposition='outside')
    
    ## Top Items chart changed from Top 10 to TOP 5
    item_df = filtered_df.groupby("Item").agg(
        Sales=('Sales','sum'),
        Weight=('Weight','sum'),
        Profit=('Profit','sum')
    ).reset_index().sort_values("Sales", ascending=False)
    
    fig_bar_item = px.bar(item_df.head(5), x="Sales", y="Item", orientation="h",
                          text="Sales", color="Profit", color_continuous_scale="Viridis",
                          template="plotly_white", title="Top 5 Items Sold (by Sales)")
    fig_bar_item.update_traces(texttemplate='AED %{text:.2s}', textposition='outside')
    
    left_col, right_col = st.columns(2)
    with left_col:
        st.plotly_chart(fig_cat_bar, use_container_width=True)
    with right_col:
        st.plotly_chart(fig_bar_item, use_container_width=True)


    # ---- TIME ANALYSIS ----
    st.subheader("📈 Sales & Profit Over Time")
    daily_summary = filtered_df.groupby(pd.Grouper(key="Date", freq="D")).agg(Sales=("Sales","sum"), Profit=("Profit","sum")).reset_index()
    
    ## Time series changed to an AREA CHART
    fig_area = px.area(daily_summary, x="Date", y=["Sales","Profit"], markers=False,
                       template="plotly_white", title="Daily Sales vs Profit Trend",
                       color_discrete_sequence=["#f6d365", "#fda085"])
    st.plotly_chart(fig_area, use_container_width=True)


    # ---- CATEGORY FOCUS ----
    st.subheader("🎯 Category Focus")
    
    ## Added a BUBBLE CHART for category analysis
    fig_bubble = px.scatter(
        category_df,
        x="Sales",
        y="Profit",
        size="Weight",
        color="Category",
        hover_name="Category",
        size_max=55,
        template="plotly_white",
        title="Category Performance: Sales vs. Profit (Bubble size represents Weight)"
    )
    st.plotly_chart(fig_bubble, use_container_width=True)


    # ---- SALES FORECAST (NEXT MONTH) ----
    st.subheader("📅 Next Month Sales Forecast")
    forecast_df = filtered_df.groupby("month_year")[["Sales"]].sum().reset_index()

    if len(forecast_df) > 1:
        X = np.arange(len(forecast_df)).reshape(-1, 1)
        y = forecast_df["Sales"].values
        model = LinearRegression().fit(X, y)
        next_month_index = np.array([[len(forecast_df)]])
        predicted_sales = model.predict(next_month_index)[0]
        last_month_sales = y[-1]

        ## Forecast changed to a GAUGE CHART
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = predicted_sales,
            title = {'text': "Predicted Sales vs. Last Month"},
            delta = {'reference': last_month_sales, 'increasing': {'color': "Green"}, 'decreasing': {'color': "Red"}},
            gauge = {
                'axis': {'range': [None, max(predicted_sales, last_month_sales) * 1.5]},
                'bar': {'color': "darkblue"},
                'steps' : [
                    {'range': [0, last_month_sales * 0.8], 'color': "lightgray"},
                    {'range': [last_month_sales * 0.8, last_month_sales * 1.2], 'color': "gray"}],
                'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': last_month_sales}
            }))
        st.plotly_chart(fig_gauge, use_container_width=True)
    else:
        st.info("ℹ️ Not enough monthly data to generate a sales forecast.")


    # ---- DOWNLOAD BUTTON ----
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download Filtered Data", data=csv, file_name='filtered_sales.csv', mime='text/csv')


# --- MAIN APP ROUTER ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_dashboard()
else:
    login_page()
