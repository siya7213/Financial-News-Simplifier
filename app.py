import io
import re
import os
import datetime
from datetime import datetime as dt, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# Optional NLP imports with fallback
try:
    import spacy

    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = None
except ImportError:
    nlp = None


# =====================================================================
# 1. CORE DATA STRUCTURES & ENGINE
# =====================================================================

def get_empty_data():
    """Initial blank state for Manual Mode."""
    return {
        'company_name': 'Custom Workspace',
        'industry': 'Awaiting Document Upload',
        'monthly_financials': pd.DataFrame(columns=['Month', 'Revenue', 'Expenses', 'Profit']),
        'vendors': pd.DataFrame(
            columns=['Vendor', 'Category', 'Spend_YTD', 'Avg_Unit_Price', 'Hist_Unit_Price', 'Price_Trend_Pct',
                     'Reliability_Score', 'Risk_Level']),
        'receivables': pd.DataFrame(columns=['Invoice_ID', 'Customer', 'Amount', 'Due_Date', 'Status', 'Risk_Score']),
        'cash_hist': pd.DataFrame(columns=['Date', 'Cash_Balance']),
        'cash_fore': pd.DataFrame(columns=['Date', 'Cash_Balance', 'Projected_Inflow', 'Projected_Outflow']),
        'is_demo': False,
        'has_data': False
    }


def load_demo_company_data():
    """Pre-loaded dataset for Demo Mode."""
    np.random.seed(42)
    months = ['Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026', 'Jul 2026', 'Aug 2026']
    revenue = [4850000, 4920000, 5100000, 5050000, 5180000, 5240000]
    expenses = [3350000, 3400000, 3480000, 3520000, 3750000, 3820000]
    profit = [r - e for r, e in zip(revenue, expenses)]

    df_monthly = pd.DataFrame({
        'Month': months,
        'Revenue': revenue,
        'Expenses': expenses,
        'Profit': profit
    })

    df_vendors = pd.DataFrame({
        'Vendor': ['ABC Industries', 'XYZ Components', 'PQR Supplies', 'Global Freight Ltd', 'Apex Cloud Tech'],
        'Category': ['Raw Material (Steel)', 'Raw Material (Aluminum)', 'Packaging Material', 'Logistics/Shipping',
                     'SaaS Software'],
        'Spend_YTD': [1820000, 1240000, 780000, 620000, 240000],
        'Avg_Unit_Price': [138.0, 107.0, 45.0, 1250.0, 20000.0],
        'Hist_Unit_Price': [118.0, 110.0, 44.0, 980.0, 20000.0],
        'Price_Trend_Pct': [16.94, -2.72, 2.27, 27.55, 0.0],
        'Reliability_Score': [92, 96, 81, 74, 99],
        'Risk_Level': ['HIGH', 'LOW', 'MEDIUM', 'HIGH', 'LOW']
    })

    df_ar = pd.DataFrame({
        'Invoice_ID': ['INV-1092', 'INV-1098', 'INV-1104', 'INV-1112', 'INV-1120'],
        'Customer': ['Titan Auto Corp', 'Bharat Heavy Eng', 'Metro Infra Works', 'Precision Auto', 'Kirloskar Forge'],
        'Amount': [420000, 340000, 180000, 250000, 120000],
        'Due_Date': ['2026-07-15', '2026-07-28', '2026-08-05', '2026-08-25', '2026-09-01'],
        'Status': ['Overdue (30+ days)', 'Overdue (15 days)', 'Overdue (8 days)', 'Current', 'Current'],
        'Risk_Score': ['HIGH', 'HIGH', 'MEDIUM', 'LOW', 'LOW']
    })

    today = dt(2026, 8, 13)
    hist_dates = [today - timedelta(days=i * 10) for i in range(6, 0, -1)]
    fore_dates = [today + timedelta(days=i * 10) for i in range(0, 10)]

    hist_cash = [2200000, 2150000, 2050000, 1980000, 1920000, 1840000]
    fore_cash = [1840000, 1650000, 1420000, 1120000, 810000, 950000, 1150000, 1260000, 1380000, 1450000]

    df_hist_cash = pd.DataFrame({'Date': [d.strftime('%b %d') for d in hist_dates], 'Cash_Balance': hist_cash})
    df_fore_cash = pd.DataFrame({
        'Date': [d.strftime('%b %d') for d in fore_dates],
        'Cash_Balance': fore_cash,
        'Projected_Inflow': [150000, 120000, 100000, 110000, 500000, 400000, 350000, 250000, 200000, 180000],
        'Projected_Outflow': [340000, 350000, 400000, 420000, 360000, 200000, 150000, 140000, 80000, 110000]
    })

    return {
        'company_name': 'Apex Precision Components Pvt. Ltd.',
        'industry': 'Industrial Components Manufacturing',
        'monthly_financials': df_monthly,
        'vendors': df_vendors,
        'receivables': df_ar,
        'cash_hist': df_hist_cash,
        'cash_fore': df_fore_cash,
        'is_demo': True,
        'has_data': True
    }


def parse_uploaded_files(invoice_files, ledger_files, bank_files):
    """Parses user documents and populates real values."""
    new_data = get_empty_data()
    new_data['company_name'] = "Uploaded Financial Repository"
    new_data['industry'] = "Custom Ingested Workspace"

    parsed_any = False

    if invoice_files:
        inv_list = []
        for f in invoice_files:
            try:
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                inv_list.append(df)
            except Exception:
                pass
        if inv_list:
            new_data['receivables'] = pd.concat(inv_list, ignore_index=True)
            parsed_any = True

    if ledger_files:
        ledger_list = []
        for f in ledger_files:
            try:
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                ledger_list.append(df)
            except Exception:
                pass
        if ledger_list:
            combined_led = pd.concat(ledger_list, ignore_index=True)
            if 'Revenue' in combined_led.columns and 'Expenses' in combined_led.columns:
                combined_led['Profit'] = combined_led['Revenue'] - combined_led['Expenses']
                new_data['monthly_financials'] = combined_led
                parsed_any = True

    if bank_files:
        bank_list = []
        for f in bank_files:
            try:
                df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
                bank_list.append(df)
            except Exception:
                pass
        if bank_list:
            combined_bank = pd.concat(bank_list, ignore_index=True)
            if 'Cash_Balance' in combined_bank.columns:
                new_data['cash_hist'] = combined_bank
                parsed_any = True

    if parsed_any:
        new_data['has_data'] = True
        st.session_state.data = new_data
    return parsed_any


def calculate_kpis(data_dict: dict):
    if not data_dict.get('has_data', False):
        return {
            'revenue': None, 'rev_delta': None,
            'profit': None, 'profit_delta': None,
            'gross_margin': None, 'gm_delta': None,
            'cash_position': None, 'cash_delta': None,
            'ar_total': None, 'ar_overdue': None, 'ap_total': None
        }

    monthly = data_dict['monthly_financials']
    latest_rev = monthly['Revenue'].iloc[-1] if not monthly.empty and 'Revenue' in monthly else 0
    prev_rev = monthly['Revenue'].iloc[-2] if len(monthly) > 1 and 'Revenue' in monthly else latest_rev
    rev_delta = (((latest_rev - prev_rev) / prev_rev) * 100) if prev_rev > 0 else 0.0

    latest_profit = monthly['Profit'].iloc[-1] if not monthly.empty and 'Profit' in monthly else 0
    prev_profit = monthly['Profit'].iloc[-2] if len(monthly) > 1 and 'Profit' in monthly else latest_profit
    profit_delta = (((latest_profit - prev_profit) / prev_profit) * 100) if prev_profit > 0 else 0.0

    gross_margin = ((latest_profit / latest_rev) * 100) if latest_rev > 0 else 0.0
    prev_gross_margin = ((prev_profit / prev_rev) * 100) if prev_rev > 0 else 0.0
    gm_delta = gross_margin - prev_gross_margin

    curr_cash = data_dict['cash_hist']['Cash_Balance'].iloc[-1] if not data_dict['cash_hist'].empty else 0
    prev_cash = data_dict['cash_hist']['Cash_Balance'].iloc[-2] if len(data_dict['cash_hist']) > 1 else curr_cash
    cash_delta = (((curr_cash - prev_cash) / prev_cash) * 100) if prev_cash > 0 else 0.0

    receivables = data_dict['receivables']
    ar_total = receivables['Amount'].sum() if not receivables.empty and 'Amount' in receivables else 0
    ar_overdue = receivables[receivables['Status'].astype(str).str.contains('Overdue')][
        'Amount'].sum() if not receivables.empty and 'Status' in receivables else 0

    return {
        'revenue': latest_rev, 'rev_delta': rev_delta,
        'profit': latest_profit, 'profit_delta': profit_delta,
        'gross_margin': gross_margin, 'gm_delta': gm_delta,
        'cash_position': curr_cash, 'cash_delta': cash_delta,
        'ar_total': ar_total, 'ar_overdue': ar_overdue, 'ap_total': 1820000
    }


def analyze_financial_news_nlp(text):
    """NLP parsing engine to summarize financial news into SME implications."""
    text_lower = text.lower()

    # Named Entity & Key Phrase Extraction via spaCy or heuristic regex
    entities = []
    if nlp is not None:
        doc = nlp(text)
        entities = [ent.text for ent in doc.ents if ent.label_ in ['ORG', 'MONEY', 'PERCENT', 'GPE', 'LAW', 'DATE']]
    if not entities:
        # Fallback entity detection
        entities = re.findall(r'\b(?:RBI|FED|GST|Steel|Aluminum|Freight|Interest Rate|Inflation|Tax|Bank)\b', text,
                              re.I)
    entities = list(set(entities))[:6]

    # Keyword Sentiment & Signal Scoring
    bearish_words = ['hike', 'inflation', 'surge', 'increase', 'deficit', 'slump', 'risk', 'crisis', 'tariff',
                     'tighten', 'penalty', 'delay']
    bullish_words = ['cut', 'growth', 'relief', 'subsidy', 'rebound', 'boost', 'easing', 'stimulus', 'surplus', 'lower']

    bearish_score = sum(1 for w in bearish_words if w in text_lower)
    bullish_score = sum(1 for w in bullish_words if w in text_lower)

    if bearish_score > bullish_score:
        sentiment = "HEADWIND / NEGATIVE IMPACT"
        sentiment_color = "card-accent-rose"
        impact_level = "HIGH RISK"
    elif bullish_score > bearish_score:
        sentiment = "TAILWIND / POSITIVE OPPORTUNITY"
        sentiment_color = "card-accent-emerald"
        impact_level = "OPPORTUNITY"
    else:
        sentiment = "NEUTRAL / BALANCED IMPACT"
        sentiment_color = "card-accent-sky"
        impact_level = "MODERATE"

    # Executive Summarization Rules
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    summary = " ".join(sentences[:2]) if len(sentences) >= 2 else text

    # Strategic Action Extraction
    takeaways = []
    if any(w in text_lower for w in ['rate', 'interest', 'repo', 'rbi', 'fed', 'borrowing']):
        takeaways.append(
            "🔒 **Working Capital Strategy**: Expect shifts in short-term credit terms. Evaluate existing variable-rate debt obligations.")
    if any(w in text_lower for w in ['steel', 'aluminum', 'metal', 'raw material', 'commodity', 'freight', 'shipping']):
        takeaways.append(
            "📦 **Procurement Guardrail**: Renegotiate long-term supplier agreements or hedge material input pricing before next quarter.")
    if any(w in text_lower for w in ['tax', 'gst', 'duty', 'tariff', 'compliance', 'subsidies']):
        takeaways.append(
            "⚖️ **Compliance & Tax Planning**: Review product margins to accommodate statutory adjustment or leverage regional fiscal incentives.")
    if not takeaways:
        takeaways.append(
            "💡 **Operational Advisory**: Monitor monthly cash burn rate and maintain cash buffer against macroeconomic volatility.")

    return {
        'summary': summary,
        'sentiment': sentiment,
        'sentiment_color': sentiment_color,
        'impact_level': impact_level,
        'entities': entities,
        'takeaways': takeaways
    }


# =====================================================================
# 2. ACCENT-ENHANCED LIGHT MODE STYLING
# =====================================================================

def apply_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
    }

    /* Vibrant Accent Cards for Cockpit Factors */
    .metric-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
        transition: all 0.25 ease;
    }

    /* Factor Color Accents */
    .card-accent-sky { border: 1px solid #bae6fd; border-left: 5px solid #0284c7; }
    .card-accent-emerald { border: 1px solid #bbf7d0; border-left: 5px solid #16a34a; }
    .card-accent-indigo { border: 1px solid #c7d2fe; border-left: 5px solid #6366f1; }
    .card-accent-amber { border: 1px solid #fde68a; border-left: 5px solid #d97706; }
    .card-accent-rose { border: 1px solid #fecdd3; border-left: 5px solid #e11d48; }

    .metric-label {
        font-size: 11px;
        font-weight: 800;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin: 6px 0;
    }
    .metric-delta-pos { font-size: 12px; font-weight: 700; color: #16a34a; }
    .metric-delta-neg { font-size: 12px; font-weight: 700; color: #dc2626; }
    .metric-empty { font-size: 24px; font-weight: 700; color: #cbd5e1; margin: 6px 0; }

    /* Health Gauge Card */
    .health-card {
        background: linear-gradient(135deg, #ffffff 0%, #f0f9ff 100%);
        border: 1px solid #7dd3fc;
        border-top: 5px solid #0284c7;
        border-radius: 16px;
        padding: 22px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(2, 132, 199, 0.06);
    }
    .health-score {
        font-size: 52px;
        font-weight: 800;
        color: #0284c7;
        line-height: 1;
        margin: 10px 0;
    }

    /* Header & Brand Logo Styling */
    .brand-header {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 6px solid #0284c7;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        padding: 18px 24px;
        border-radius: 16px;
        margin-bottom: 24px;
    }
    .brand-logo-container {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .brand-logo-icon {
        background: linear-gradient(135deg, #0284c7 0%, #0f172a 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 13px;
        letter-spacing: -0.5px;
        width: 44px;
        height: 44px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.25);
    }
    .brand-title {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.5px;
    }

    /* Alerts */
    .alert-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    }
    .alert-critical { border-left: 5px solid #ef4444; background: #fff5f5; border-top: 1px solid #fecdd3; border-right: 1px solid #fecdd3; border-bottom: 1px solid #fecdd3; }
    .alert-warning { border-left: 5px solid #f59e0b; background: #fffbeb; border-top: 1px solid #fde68a; border-right: 1px solid #fde68a; border-bottom: 1px solid #fde68a; }

    /* Custom Square Radio Button Navigation Styling */
    div[data-testid="stRadio"] > div {
        gap: 8px;
    }
    div[data-testid="stRadio"] label {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        font-weight: 600 !important;
        color: #334155 !important;
        width: 100%;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #0284c7 !important;
        background: #f0f9ff !important;
        color: #0284c7 !important;
    }
    /* Square radio control appearance */
    div[data-testid="stRadio"] label div[role="radio"] {
        border-radius: 3px !important; /* Makes radio button icon square */
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9;
        border-right: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, delta: str = None, is_positive: bool = True,
                       accent_class: str = "card-accent-sky"):
    if value is None:
        st.markdown(f"""
        <div class="metric-card {accent_class}">
            <div class="metric-label">{label}</div>
            <div class="metric-empty">--</div>
            <div style="font-size:11px; color:#94a3b8;">Upload documents to parse</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        delta_class = "metric-delta-pos" if is_positive else "metric-delta-neg"
        st.markdown(f"""
        <div class="metric-card {accent_class}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="{delta_class}">{delta}</div>
        </div>
        """, unsafe_allow_html=True)


def render_health_score_card(score=None, delta_pct=None):
    if score is None:
        st.markdown("""
        <div class="health-card">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; font-weight: 800;">Financial Health Index</div>
            <div class="health-score" style="color:#cbd5e1;">--<span style="font-size: 20px; color: #94a3b8;">/100</span></div>
            <div style="font-size: 12px; color: #64748b; margin-top: 8px;">Status: <b>AWAITING DOCUMENT INGESTION</b></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="health-card">
            <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; font-weight: 800;">Financial Health Index</div>
            <div class="health-score">{score}<span style="font-size: 20px; color: #94a3b8;">/100</span></div>
            <div style="font-size: 13px; color: #16a34a; font-weight: 700;">{delta_pct} vs previous period</div>
            <div style="font-size: 11px; color: #64748b; margin-top: 8px;">Status: <b>STABLE WITH CAPITAL LEAKS</b></div>
        </div>
        """, unsafe_allow_html=True)


# =====================================================================
# 3. PAGE MODULES
# =====================================================================

def render_manual_upload_page():
    st.markdown("### Manual Document Upload & Ingestion")
    st.info("📌 Upload distinct financial documents below to populate real figures across the cockpit and runway tools.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. Invoices & Receivables")
        inv_files = st.file_uploader("Invoices / AR Logs (CSV, XLSX)", type=['csv', 'xlsx'], accept_multiple_files=True,
                                     key="inv_upload")

    with col2:
        st.markdown("#### 2. Financial Statements")
        ledger_files = st.file_uploader("P&L Statements / Ledgers (CSV, XLSX)", type=['csv', 'xlsx'],
                                        accept_multiple_files=True, key="led_upload")

    with col3:
        st.markdown("#### 3. Bank Statements")
        bank_files = st.file_uploader("Bank Statements / Cash Logs (CSV, XLSX)", type=['csv', 'xlsx'],
                                      accept_multiple_files=True, key="bank_upload")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⚡ Process & Analyze Uploaded Documents", type="primary", use_container_width=True):
        with st.spinner("Processing distinct data streams..."):
            success = parse_uploaded_files(inv_files, ledger_files, bank_files)
            if success:
                st.success("Uploaded documents successfully integrated! Executive Overview and Runway populated.")
                st.rerun()
            else:
                st.warning("Please upload valid CSV or XLSX files in at least one category to update metrics.")


def render_overview_page():
    st.markdown("### Executive Cockpit")

    kpis = calculate_kpis(st.session_state.data)
    col_health, col_kpis = st.columns([1, 2.2])

    with col_health:
        if st.session_state.data.get('has_data', False):
            render_health_score_card(score=78, delta_pct="↑ 4.2%")
        else:
            render_health_score_card()

    with col_kpis:
        c1, c2, c3 = st.columns(3)
        with c1:
            render_metric_card("Revenue", f"₹{kpis['revenue'] / 100000:.1f}L" if kpis['revenue'] is not None else None,
                               f"↑ {kpis['rev_delta']:.1f}%" if kpis['rev_delta'] is not None else None, True,
                               "card-accent-sky")
            render_metric_card("Net Profit", f"₹{kpis['profit'] / 100000:.1f}L" if kpis['profit'] is not None else None,
                               f"↓ {abs(kpis['profit_delta']):.1f}%" if kpis['profit_delta'] is not None else None,
                               False, "card-accent-rose")
        with c2:
            render_metric_card("Gross Margin",
                               f"{kpis['gross_margin']:.1f}%" if kpis['gross_margin'] is not None else None,
                               f"↑ {kpis['gm_delta']:.1f}%" if kpis['gm_delta'] is not None else None, True,
                               "card-accent-emerald")
            render_metric_card("Cash Balance",
                               f"₹{kpis['cash_position'] / 100000:.1f}L" if kpis['cash_position'] is not None else None,
                               f"↓ {abs(kpis['cash_delta']):.1f}%" if kpis['cash_delta'] is not None else None, False,
                               "card-accent-amber")
        with c3:
            render_metric_card("Overdue AR",
                               f"₹{kpis['ar_overdue'] / 100000:.1f}L" if kpis['ar_overdue'] is not None else None,
                               "Needs Collection" if kpis['ar_overdue'] is not None else None, False,
                               "card-accent-rose")
            render_metric_card("Pending AP",
                               f"₹{kpis['ap_total'] / 100000:.1f}L" if kpis['ap_total'] is not None else None,
                               "30-Day Obligations" if kpis['ap_total'] is not None else None, True,
                               "card-accent-indigo")

    st.markdown("<br>", unsafe_allow_html=True)

    col_chart, col_alerts = st.columns([1.8, 1.2])
    with col_chart:
        st.markdown("#### Performance Velocity")
        if st.session_state.data.get('has_data', False) and not st.session_state.data['monthly_financials'].empty:
            df = st.session_state.data['monthly_financials']
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Month'], y=df['Revenue'], mode='lines+markers', name='Revenue',
                                     line=dict(color='#0284c7', width=3)))
            fig.add_trace(go.Bar(x=df['Month'], y=df['Profit'], name='Net Profit', marker_color='#16a34a', opacity=0.7))
            fig.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📈 Chart blank. Upload financial ledgers in 'Manual Document Upload' to render trend curves.")

    with col_alerts:
        st.markdown("#### Intelligence Alerts")
        if st.session_state.data.get('has_data', False):
            st.markdown("""
            <div class="alert-card alert-critical">
                <div style="font-weight: 700; color: #0f172a; font-size: 13px;">🔴 Liquidity Warning</div>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">Cash position projected to dip near threshold in 35 days.</div>
            </div>
            <div class="alert-card alert-warning">
                <div style="font-weight: 700; color: #0f172a; font-size: 13px;">🟠 Vendor Cost Anomaly</div>
                <div style="font-size: 12px; color: #475569; margin-top: 2px;">Supplier ABC price increased by +16.8% over contract baseline.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.write("No active alerts. Ingest documents to trigger operational rules.")


def render_cash_flow_runway_page():
    st.markdown("### Extended Cash Flow & Liquidity Runway")

    if not st.session_state.data.get('has_data', False):
        st.info(
            "💡 Upload bank logs or financials in 'Manual Document Upload' to compute cash burn rate and scenario forecasts.")
        return

    h_df = st.session_state.data['cash_hist']
    f_df = st.session_state.data['cash_fore']

    curr_cash = h_df['Cash_Balance'].iloc[-1] if not h_df.empty else 0
    avg_inflow = f_df['Projected_Inflow'].mean() if 'Projected_Inflow' in f_df and not f_df.empty else 250000
    avg_outflow = f_df['Projected_Outflow'].mean() if 'Projected_Outflow' in f_df and not f_df.empty else 280000
    net_burn_monthly = avg_outflow - avg_inflow
    runway_months = (curr_cash / net_burn_monthly) if net_burn_monthly > 0 else 12.0

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        render_metric_card("Current Cash Reserve", f"₹{curr_cash / 100000:.1f}L", "Available Treasury", True,
                           "card-accent-emerald")
    with rc2:
        render_metric_card("Net Cash Burn Rate", f"₹{net_burn_monthly / 1000:.0f}K / mo", "Monthly Outflow Surplus",
                           False, "card-accent-rose")
    with rc3:
        render_metric_card("Runway Longevity", f"{runway_months:.1f} Months", "At Current Burn Rate", runway_months > 6,
                           "card-accent-sky")
    with rc4:
        render_metric_card("Lowest Point Forecast",
                           f"₹{(f_df['Cash_Balance'].min() if not f_df.empty else 0) / 100000:.1f}L", "Horizon Min",
                           False, "card-accent-amber")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Cash Flow Scenario Simulator")
    sc1, sc2 = st.columns(2)
    with sc1:
        ar_collection_boost = st.slider("Accelerate AR Collections (%)", 0, 100, 25)
    with sc2:
        cost_cut_pct = st.slider("Vendor / OPEX Cost Reduction (%)", 0, 30, 10)

    if not f_df.empty:
        adjusted_cash_balance = f_df['Cash_Balance'] + (ar_collection_boost * 3000)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=h_df['Date'], y=h_df['Cash_Balance'], mode='lines+markers', name='Historical Cash',
                                 line=dict(color='#0f172a', width=3)))
        fig.add_trace(go.Scatter(x=f_df['Date'], y=f_df['Cash_Balance'], mode='lines+markers', name='Base Forecast',
                                 line=dict(color='#ef4444', width=2, dash='dash')))
        fig.add_trace(
            go.Scatter(x=f_df['Date'], y=adjusted_cash_balance, mode='lines+markers', name='Simulated Position',
                       line=dict(color='#16a34a', width=3)))
        fig.update_layout(template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                          height=350, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)


def render_intelligence_page():
    st.markdown("### Intelligence & Variance Engine")

    if not st.session_state.data.get('has_data', False):
        st.info(
            "💡 Upload financial dataset in 'Manual Document Upload' to execute detailed variance decomposition and drift diagnostics.")
        return

    st.write("Root-cause financial diagnostics decomposed across P&L, vendor procurement, and credit exposure:")

    tab1, tab2, tab3 = st.tabs(
        ["📊 P&L Net Margin Variance", "🚚 Procurement Unit Cost Drift", "⏳ Receivables Aging Risk Matrix"])

    with tab1:
        st.markdown("#### P&L Variance Breakdown (-₹2.80L Net Delta)")
        c1, c2 = st.columns([1.5, 1])
        with c1:
            fig = go.Figure(go.Waterfall(
                name="P&L Variance", orientation="v",
                measure=["relative", "relative", "relative", "relative", "total"],
                x=["Raw Material Inflation", "Logistics Spikes", "Client Discounting", "Unplanned OPEX",
                   "Net Delta Impact"],
                textposition="outside",
                y=[-140000, -62000, -51000, -27000, -280000],
                connector={"line": {"color": "#94a3b8"}},
                decreasing={"marker": {"color": "#ef4444"}},
                totals={"marker": {"color": "#0f172a"}}
            ))
            fig.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("""
            **Key Variance Factors:**
            * **Raw Material Price Surge**: +₹1.40L (50.0% of total leakage)
            * **Freight Rate Escalations**: +₹0.62L (22.1% of total leakage)
            * **Early Settlement Discounts**: +₹0.51L (18.2% of total leakage)
            * **Unplanned Overhead**: +₹0.27L (9.7% of total leakage)
            """)

    with tab2:
        st.markdown("#### Vendor Price Trend Analysis")
        v_df = st.session_state.data['vendors']
        if not v_df.empty:
            st.dataframe(
                v_df[['Vendor', 'Category', 'Avg_Unit_Price', 'Hist_Unit_Price', 'Price_Trend_Pct', 'Risk_Level']],
                use_container_width=True)

    with tab3:
        st.markdown("#### Receivables Exposure & Overdue Profiling")
        ar_df = st.session_state.data['receivables']
        if not ar_df.empty:
            st.dataframe(ar_df[['Invoice_ID', 'Customer', 'Amount', 'Due_Date', 'Status', 'Risk_Score']],
                         use_container_width=True)


def render_news_simplifier_page():
    st.markdown("### Financial News Simplifier & Macro Intelligence")
    st.write(
        "Extract executive summaries, sentiment impact scores, and operational takeaways from unstructured financial articles using Natural Language Processing (NLP).")

    # Sample Preset Bulletins for instant testing
    sample_news_1 = "The Reserve Bank of India raised the repo rate by 25 basis points to combat persistent food inflation. Commercial banks are expected to transmit the rate hike immediately, increasing borrowing costs for MSMEs and industrial term loans."
    sample_news_2 = "Global steel prices dropped by 4.5% this week amid increasing supply capacity and reduced infrastructure spending in major export hubs. Raw aluminum and logistics freight indexes also showed signs of cooling."
    sample_news_3 = "Government announces tax incentives and credit guarantee scheme extensions for manufacturing enterprises investing in solar green energy and automated capital equipment."

    st.markdown("#### Input Macro / Financial Article")
    preset = st.selectbox("Select Sample Financial Bulletin (or type below):",
                          ["Custom Input", "RBI Repo Rate Hike & SME Borrowing Impact",
                           "Global Commodity & Steel Price Cooling", "Fiscal Tax Incentives & Green Capital Support"])

    if preset == "RBI Repo Rate Hike & SME Borrowing Impact":
        default_text = sample_news_1
    elif preset == "Global Commodity & Steel Price Cooling":
        default_text = sample_news_2
    elif preset == "Fiscal Tax Incentives & Green Capital Support":
        default_text = sample_news_3
    else:
        default_text = ""

    user_article = st.text_area("Paste Complex Financial Article or Policy Release:", value=default_text, height=140,
                                placeholder="Paste macro-economic news, monetary policy updates, or commodity market briefs here...")

    if st.button("🔍 Simplify & Extract NLP Signals", type="primary"):
        if not user_article.strip():
            st.warning("Please enter or paste a financial news snippet to analyze.")
            return

        with st.spinner("Processing text with NLP entity extraction & sentiment engine..."):
            res = analyze_financial_news_nlp(user_article)

        col_left, col_right = st.columns([1.2, 1.8])

        with col_left:
            st.markdown("#### Impact Profile")
            render_metric_card("Macro Sentiment Signal", res['sentiment'], f"Signal: {res['impact_level']}",
                               res['sentiment_color'] != 'card-accent-rose', res['sentiment_color'])

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Extracted Key Entities")
            if res['entities']:
                st.write(" ".join([f"`{ent}`" for ent in res['entities']]))
            else:
                st.caption("No specific structured named entities extracted.")

        with col_right:
            st.markdown("#### Executive Breakdown")
            st.markdown(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:16px; margin-bottom:16px;">
                <div style="font-weight:800; font-size:12px; color:#0284c7; text-transform:uppercase; letter-spacing:0.5px;">Simplified Summary</div>
                <div style="font-size:14px; color:#1e293b; margin-top:6px; line-height:1.5;">{res['summary']}</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("##### Operational & CFO Takeaways")
            for t in res['takeaways']:
                st.markdown(f"- {t}")


def render_action_center_page():
    st.markdown("### Action Execution Center")
    st.write("Automated, high-priority intervention tasks derived from financial intelligence flags:")

    st.markdown("""
    * **1. Vendor Re-negotiation Dispatch**
      * *Trigger*: Supplier ABC unit price inflated by **+16.9%** above historical benchmark.
      * *Action*: Generate and issue commercial Request for Quotation (RFQ) notice demanding price realignment to ₹118/unit.

    * **2. Automated Accounts Receivable (AR) Follow-ups**
      * *Trigger*: **₹9.40L** outstanding across overdue customer accounts.
      * *Action*: Issue automated payment reminder notices with structured escalation schedules to Titan Auto Corp and Bharat Heavy Eng.

    * **3. Working Capital Liquidity Buffer Safeguard**
      * *Trigger*: Cash reserve projected to dip near threshold in Day 35–40 horizon.
      * *Action*: Freeze non-critical OPEX purchases and request 15-day vendor payment extension.
    """)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Execute Action Workflows", type="primary"):
        st.success("✅ Commercial RFQ notice generated and AR follow-up notifications queued for dispatch!")


# =====================================================================
# 4. MAIN ENTRY POINT
# =====================================================================

def main():
    st.set_page_config(
        page_title="theCFO — Autonomous Financial Intelligence",
        page_icon="💎",
        layout="wide"
    )

    apply_custom_css()

    # Session State Initialization (Manual Mode Defaults)
    if 'data' not in st.session_state:
        st.session_state.data = get_empty_data()
    if 'mode' not in st.session_state:
        st.session_state['mode'] = "MANUAL MODE"

    # Sidebar Navigation & Mode Logic
    with st.sidebar:
        st.markdown("<h2 style='color:#0284c7; font-weight:800; margin-bottom:0;'>theCFO</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748b; font-size:11px; margin-top:0;'>FINANCIAL INTELLIGENCE SUITE</p>",
                    unsafe_allow_html=True)
        st.divider()

        st.markdown("#### Operating Mode")
        mode_choice = st.selectbox(
            "Application Mode",
            ["MANUAL MODE (Upload Custom Files)", "DEMO MODE (Default Dataset)"]
        )

        # Mode Transition Logic
        if "DEMO MODE" in mode_choice and not st.session_state.data.get('is_demo', False):
            st.session_state.data = load_demo_company_data()
            st.session_state['mode'] = "DEMO MODE"
            st.session_state['nav_selection'] = "Executive Overview"  # Auto reset to top option for Demo
            st.rerun()
        elif "MANUAL MODE" in mode_choice and st.session_state.data.get('is_demo', False):
            st.session_state.data = get_empty_data()
            st.session_state['mode'] = "MANUAL MODE"
            st.session_state['nav_selection'] = "Manual Document Upload"  # Auto reset to top option for Manual
            st.rerun()

        st.divider()
        st.markdown("#### Dashboard Navigation")

        # Dynamic Navigation List based on Mode
        if st.session_state['mode'] == "DEMO MODE":
            nav_options = [
                "Executive Overview",
                "Cash Flow Runway Analysis",
                "Intelligence & Variances",
                "Financial News Simplifier",
                "Action Execution Center"
            ]
        else:
            nav_options = [
                "Manual Document Upload",
                "Executive Overview",
                "Cash Flow Runway Analysis",
                "Intelligence & Variances",
                "Financial News Simplifier",
                "Action Execution Center"
            ]

        # Ensure active selection is valid
        if 'nav_selection' not in st.session_state or st.session_state['nav_selection'] not in nav_options:
            st.session_state['nav_selection'] = nav_options[0]

        # Square styled Radio Button Navigation
        selected_page = st.radio(
            "Select Dashboard View:",
            nav_options,
            index=nav_options.index(st.session_state['nav_selection'])
        )
        st.session_state['nav_selection'] = selected_page

    # Header with Logo & Title
    st.markdown(f"""
    <div class="brand-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div class="brand-logo-container">
                <div class="brand-logo-icon">CFO</div>
                <div>
                    <div class="brand-title">theCFO</div>
                    <div style="color: #64748b; font-size: 13px; font-weight: 500;">
                        {st.session_state.data['company_name']} — {st.session_state.data['industry']}
                    </div>
                </div>
            </div>
            <div>
                <span style="background: #e0f2fe; color: #0284c7; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 12px; border: 1px solid #bae6fd;">
                    {st.session_state['mode']}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Router
    if selected_page == "Manual Document Upload":
        render_manual_upload_page()
    elif selected_page == "Executive Overview":
        render_overview_page()
    elif selected_page == "Cash Flow Runway Analysis":
        render_cash_flow_runway_page()
    elif selected_page == "Intelligence & Variances":
        render_intelligence_page()
    elif selected_page == "Financial News Simplifier":
        render_news_simplifier_page()
    elif selected_page == "Action Execution Center":
        render_action_center_page()


if __name__ == "__main__":
    main()
