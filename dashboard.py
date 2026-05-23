"""
dashboard.py — Dawn Bot Live Monitor
Deploy free on streamlit.io — reads from Google Sheets
"""

import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
import json

# ── PAGE CONFIG ──
st.set_page_config(
    page_title="Dawn Bot Monitor",
    page_icon="🌄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── STYLES ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

* { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e8f0; }

.metric-card {
    background: linear-gradient(135deg, #12121f 0%, #1a1a2e 100%);
    border: 1px solid #2a2a4a;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin: 4px;
}
.metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: #6666aa;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 28px;
    font-weight: 700;
    color: #e8e8f0;
}
.metric-value.green { color: #00ff88; }
.metric-value.red { color: #ff4466; }
.metric-value.yellow { color: #ffcc00; }

.bot-header {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    color: #8888cc;
    text-transform: uppercase;
    letter-spacing: 3px;
    padding: 8px 0;
    border-bottom: 1px solid #2a2a4a;
    margin-bottom: 16px;
}
.trade-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 12px;
    border-radius: 6px;
    margin: 3px 0;
    font-size: 13px;
    font-family: 'Space Mono', monospace;
}
.trade-win { background: rgba(0,255,136,0.08); border-left: 3px solid #00ff88; }
.trade-loss { background: rgba(255,68,102,0.08); border-left: 3px solid #ff4466; }
.dawn-title {
    font-family: 'Space Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #ffcc00;
    letter-spacing: 4px;
}
.subtitle {
    font-family: 'DM Sans', sans-serif;
    color: #6666aa;
    font-size: 14px;
    margin-top: -8px;
}
.section-title {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: #6666aa;
    text-transform: uppercase;
    letter-spacing: 3px;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a2a4a;
}
</style>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS CONNECTION ──
SHEET_ID = st.secrets["SHEET_ID"]
BOT_TABS = {
    "Dawn Lite Live": "DawnLiteLive",
    "Dawn Lite":      "DawnLite",
    "Dawn Bot":       "DawnBot",
    "Dawn V2":        "DawnV2",
    "XGB4":           "XGB4",
}
BOT_STAKES = {
    "Dawn Lite Live": "£ GBP",
    "Dawn Lite": "$9",
    "Dawn Bot": "$10",
    "Dawn V2": "$7",
    "XGB4": "$8",
}
BOT_COLORS = {
    "Dawn Lite Live": "#ffcc00",
    "Dawn Lite": "#00ff88",
    "Dawn Bot": "#4488ff",
    "Dawn V2": "#ff88ff",
    "XGB4": "#ff8844",
}

@st.cache_resource(ttl=30)
def get_sheet_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=30)
def load_bot_data(tab_name):
    try:
        gc = get_sheet_client()
        sheet = gc.open_by_key(SHEET_ID)
        ws = sheet.worksheet(tab_name)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df = df[df['outcome'].isin(['WIN','LOSS'])]
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['pnl'] = pd.to_numeric(df['pnl'], errors='coerce').fillna(0)
        df['ml_prob'] = pd.to_numeric(df['ml_prob'], errors='coerce').fillna(0)
        return df.sort_values('timestamp', ascending=False)
    except Exception as e:
        return pd.DataFrame()

def calc_stats(df):
    if df.empty or len(df) == 0:
        return {"trades": 0, "wins": 0, "losses": 0, "wr": 0, "pnl": 0, "streak": 0}
    wins = (df['outcome']=='WIN').sum()
    losses = (df['outcome']=='LOSS').sum()
    wr = wins/len(df)*100 if len(df) > 0 else 0
    pnl = df['pnl'].sum()
    # Current streak
    streak = 0
    last = None
    for o in df['outcome']:
        if last is None:
            last = o; streak = 1
        elif o == last:
            streak += 1
        else:
            break
    streak_val = streak if last == 'WIN' else -streak
    return {"trades": len(df), "wins": int(wins), "losses": int(losses),
            "wr": wr, "pnl": pnl, "streak": streak_val}

def wr_color(wr):
    if wr >= 58: return "green"
    if wr >= 52.2: return "yellow"
    return "red"

def pnl_color(pnl):
    return "green" if pnl >= 0 else "red"

# ── HEADER ──
col1, col2 = st.columns([3,1])
with col1:
    st.markdown('<div class="dawn-title">🌄 DAWN BOT MONITOR</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Live performance across all bots — auto-refreshes every 30s</div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div style="text-align:right; font-family: Space Mono; font-size:12px; color:#6666aa; padding-top:16px;">{datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh", type="secondary"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ── LOAD ALL DATA ──
all_data = {}
for bot_name, tab in BOT_TABS.items():
    all_data[bot_name] = load_bot_data(tab)

# ── BOT SUMMARY CARDS ──
st.markdown('<div class="section-title">Bot Performance Summary</div>', unsafe_allow_html=True)
cols = st.columns(len(BOT_TABS))

for i, (bot_name, df) in enumerate(all_data.items()):
    stats = calc_stats(df)
    color = BOT_COLORS[bot_name]
    wr_cls = wr_color(stats['wr'])
    pnl_cls = pnl_color(stats['pnl'])
    streak_str = f"{'🔥' if stats['streak'] > 0 else '❄️'} {abs(stats['streak'])}{'W' if stats['streak'] > 0 else 'L'}"

    with cols[i]:
        st.markdown(f"""
        <div class="metric-card" style="border-top: 3px solid {color}">
            <div class="metric-label">{bot_name}</div>
            <div class="metric-label" style="color:{color}; font-size:10px">{BOT_STAKES.get(bot_name,'')}</div>
            <div class="metric-value {wr_cls}">{stats['wr']:.1f}%</div>
            <div style="font-size:11px; color:#6666aa; margin:4px 0">WR</div>
            <div class="metric-value {pnl_cls}" style="font-size:20px">{'£' if 'Live' in bot_name else '$'}{stats['pnl']:+.2f}</div>
            <div style="font-size:11px; color:#6666aa; margin:4px 0">PnL</div>
            <div style="font-size:13px; color:#aaaacc; margin-top:8px">{stats['wins']}W / {stats['losses']}L ({stats['trades']} trades)</div>
            <div style="font-size:12px; color:#888888; margin-top:4px">{streak_str if stats['trades'] > 0 else '—'}</div>
        </div>
        """, unsafe_allow_html=True)

# ── PNL CHART ──
st.markdown('<div class="section-title">Cumulative PnL Over Time</div>', unsafe_allow_html=True)

fig = go.Figure()
for bot_name, df in all_data.items():
    if df.empty:
        continue
    df_sorted = df.sort_values('timestamp')
    df_sorted['cumulative_pnl'] = df_sorted['pnl'].cumsum()
    fig.add_trace(go.Scatter(
        x=df_sorted['timestamp'],
        y=df_sorted['cumulative_pnl'],
        name=bot_name,
        line=dict(color=BOT_COLORS[bot_name], width=2),
        mode='lines+markers',
        marker=dict(size=4),
    ))

fig.add_hline(y=0, line_dash="dash", line_color="#444466", opacity=0.5)
fig.update_layout(
    paper_bgcolor='#0a0a0f',
    plot_bgcolor='#12121f',
    font=dict(family='Space Mono', color='#aaaacc', size=11),
    legend=dict(bgcolor='#12121f', bordercolor='#2a2a4a', borderwidth=1),
    xaxis=dict(gridcolor='#1a1a2e', showgrid=True),
    yaxis=dict(gridcolor='#1a1a2e', showgrid=True, title="PnL"),
    height=320,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── EXPIRY SWEET SPOT ──
st.markdown('<div class="section-title">Expiry Sweet Spot Analysis</div>', unsafe_allow_html=True)

expiry_cols = st.columns(len(all_data))
for i, (bot_name, df) in enumerate(all_data.items()):
    with expiry_cols[i]:
        st.markdown(f'<div style="font-family:Space Mono; font-size:11px; color:{BOT_COLORS[bot_name]}; margin-bottom:8px">{bot_name}</div>', unsafe_allow_html=True)
        if df.empty:
            st.markdown('<div style="color:#444466; font-size:12px">No data</div>', unsafe_allow_html=True)
            continue
        rows = []
        for mins in [7, 15, 20, 30, 45, 60]:
            col = f'win_{mins}min'
            if col not in df.columns:
                continue
            s = df[df[col].isin(['WIN','LOSS'])]
            if len(s) < 5:
                continue
            wr = (s[col]=='WIN').mean()*100
            rows.append({"Expiry": f"{mins}min", "WR": f"{wr:.1f}%", "n": len(s)})
        if rows:
            exp_df = pd.DataFrame(rows)
            st.dataframe(exp_df, hide_index=True, use_container_width=True,
                        column_config={"WR": st.column_config.TextColumn("WR")})

# ── SYMBOL BREAKDOWN ──
st.markdown('<div class="section-title">Symbol Breakdown</div>', unsafe_allow_html=True)

sym_cols = st.columns(len(all_data))
for i, (bot_name, df) in enumerate(all_data.items()):
    with sym_cols[i]:
        st.markdown(f'<div style="font-family:Space Mono; font-size:11px; color:{BOT_COLORS[bot_name]}; margin-bottom:8px">{bot_name}</div>', unsafe_allow_html=True)
        if df.empty:
            st.markdown('<div style="color:#444466; font-size:12px">No data</div>', unsafe_allow_html=True)
            continue
        rows = []
        for sym, grp in df.groupby('symbol'):
            w = (grp['outcome']=='WIN').sum()
            t = len(grp)
            p = grp['pnl'].sum()
            rows.append({"Symbol": sym, "WR": f"{w/t*100:.0f}%", "PnL": f"${p:.2f}", "n": t})
        if rows:
            sym_df = pd.DataFrame(rows).sort_values('n', ascending=False)
            st.dataframe(sym_df, hide_index=True, use_container_width=True)

# ── RECENT TRADES FEED ──
st.markdown('<div class="section-title">Recent Trades Feed</div>', unsafe_allow_html=True)

all_trades = []
for bot_name, df in all_data.items():
    if not df.empty:
        temp = df.head(20).copy()
        temp['bot'] = bot_name
        all_trades.append(temp)

if all_trades:
    combined = pd.concat(all_trades).sort_values('timestamp', ascending=False).head(30)
    for _, row in combined.iterrows():
        win = row['outcome'] == 'WIN'
        cls = 'trade-win' if win else 'trade-loss'
        emoji = '✅' if win else '❌'
        pnl_str = f"{'£' if 'Live' in row['bot'] else '$'}{row['pnl']:+.2f}"
        prob_str = f"{row['ml_prob']*100:.1f}%" if row['ml_prob'] > 0 else "—"
        time_str = pd.to_datetime(row['timestamp']).strftime('%H:%M')
        st.markdown(f"""
        <div class="trade-row {cls}">
            <span>{emoji} <b>{row['symbol']}</b> {row['direction']}</span>
            <span style="color:#8888cc">{row['bot']}</span>
            <span>prob: {prob_str}</span>
            <span style="color:{'#00ff88' if win else '#ff4466'}">{pnl_str}</span>
            <span style="color:#555577">{time_str}</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align:center; font-family:Space Mono; font-size:10px; color:#333355">DAWN BOT MONITOR • Auto-refreshes every 30s • Breakeven: 52.2% WR</div>', unsafe_allow_html=True)

# Auto refresh
st.markdown("""
<script>
setTimeout(function() { window.location.reload(); }, 30000);
</script>
""", unsafe_allow_html=True)
