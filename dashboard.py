"""
dashboard.py — Dawn Bot Live Monitor
Deploy free on streamlit.io — reads from Google Sheets
Theme: Gold & White — clean, bright, professional
"""

import streamlit as st
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import plotly.graph_objects as go
import json

st.set_page_config(
    page_title="Dawn Bot Monitor",
    page_icon="🌄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
* { font-family: 'Inter', sans-serif; font-weight: 500; }
.stApp { background: #fafafa; color: #111827; }
[data-testid="stAppViewContainer"] { background: #fafafa; }
[data-testid="stHeader"] { background: #fafafa; }
.dawn-header { display:flex; align-items:center; gap:12px; padding:8px 0 4px 0; border-bottom:3px solid #f59e0b; margin-bottom:24px; }
.dawn-title { font-size:28px; font-weight:800; color:#78350f; letter-spacing:2px; }
.dawn-subtitle { font-size:13px; color:#374151; font-weight:500; margin-top:2px; }
.dawn-time { margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:11px; color:#9ca3af; }
.metric-card { background:#ffffff; border:0.5px solid #e5e7eb; border-radius:12px; padding:18px 16px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.06); margin:2px; }
.metric-bot-name { font-size:10px; font-weight:700; color:#374151; text-transform:uppercase; letter-spacing:2px; margin-bottom:2px; }
.metric-stake { font-size:11px; font-weight:700; margin-bottom:10px; }
.metric-wr { font-family:'JetBrains Mono',monospace; font-size:30px; font-weight:700; margin-bottom:2px; }
.metric-wr-label { font-size:11px; color:#6b7280; font-weight:600; margin-bottom:8px; }
.metric-pnl { font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:600; margin-bottom:2px; }
.metric-pnl-label { font-size:11px; color:#6b7280; font-weight:600; margin-bottom:8px; }
.metric-trades { font-size:12px; color:#111827; font-weight:600; margin-bottom:4px; }
.metric-streak { font-size:12px; color:#374151; font-weight:600; }
.green { color:#059669; } .red { color:#dc2626; } .amber { color:#d97706; } .gray { color:#6b7280; }
.section-title { font-size:11px; font-weight:800; color:#374151; text-transform:uppercase; letter-spacing:3px; margin:28px 0 12px 0; padding-bottom:6px; border-bottom:2px solid #f59e0b; }
.trade-feed { background:#ffffff; border:0.5px solid #e5e7eb; border-radius:10px; overflow:hidden; box-shadow:0 1px 4px rgba(0,0,0,0.04); }
.trade-row { display:flex; align-items:center; gap:12px; padding:9px 14px; border-bottom:0.5px solid #f3f4f6; font-size:12px; }
.trade-row:last-child { border-bottom:none; }
.trade-win { border-left:3px solid #059669; }
.trade-loss { border-left:3px solid #dc2626; }
.trade-sym { font-weight:700; color:#111827; min-width:70px; font-size:13px; }
.trade-dir { color:#374151; font-weight:600; min-width:40px; }
.trade-bot { color:#374151; font-size:11px; font-weight:600; flex:1; }
.trade-prob { font-family:'JetBrains Mono',monospace; color:#374151; font-weight:600; font-size:11px; min-width:48px; }
.trade-pnl { font-family:'JetBrains Mono',monospace; font-weight:600; min-width:58px; text-align:right; }
.trade-time { color:#6b7280; font-size:11px; font-weight:600; min-width:44px; text-align:right; }
.breakeven-bar { background:#fffbeb; border:1px solid #fcd34d; border-radius:6px; padding:10px 16px; display:flex; align-items:center; gap:12px; margin:8px 0; font-size:12px; font-weight:600; color:#374151; flex-wrap:wrap; }
</style>
""", unsafe_allow_html=True)

SHEET_ID = st.secrets["SHEET_ID"]
BOT_TABS = {
    "Dawn Lite Live": "DawnLiteLive",
    "Dawn Lite":      "DawnLite",
    "Dawn Bot":       "DawnBot",
    "Dawn V2":        "DawnV2",
    "XGB4":           "XGB4",
}
BOT_STAKES = {
    "Dawn Lite Live": "£ GBP Live",
    "Dawn Lite":      "$9 Demo",
    "Dawn Bot":       "$10 Demo",
    "Dawn V2":        "$7 Demo",
    "XGB4":           "$8 Demo",
}
BOT_COLORS = {
    "Dawn Lite Live": "#f59e0b",
    "Dawn Lite":      "#059669",
    "Dawn Bot":       "#2563eb",
    "Dawn V2":        "#7c3aed",
    "XGB4":           "#dc2626",
}

@st.cache_resource(ttl=30)
def get_sheet_client():
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
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
    except:
        return pd.DataFrame()

def calc_stats(df):
    if df.empty:
        return {"trades":0,"wins":0,"losses":0,"wr":0,"pnl":0,"streak":0}
    wins = (df['outcome']=='WIN').sum()
    wr = wins/len(df)*100
    pnl = df['pnl'].sum()
    streak = 0; last = None
    for o in df['outcome']:
        if last is None: last=o; streak=1
        elif o==last: streak+=1
        else: break
    return {"trades":len(df),"wins":int(wins),"losses":int(len(df)-wins),"wr":wr,"pnl":pnl,"streak":streak if last=='WIN' else -streak}

def wr_cls(wr): return "green" if wr>=58 else ("amber" if wr>=52.2 else "red")
def pnl_cls(pnl): return "green" if pnl>=0 else "red"

# HEADER
col1, col2 = st.columns([4,1])
with col1:
    st.markdown(f'''<div class="dawn-header"><span style="font-size:28px">🌄</span><div><div class="dawn-title">DAWN BOT MONITOR</div><div class="dawn-subtitle">Live performance across all bots — auto-refreshes every 30s</div></div><div class="dawn-time">{datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</div></div>''', unsafe_allow_html=True)
with col2:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

all_data = {bot: load_bot_data(tab) for bot, tab in BOT_TABS.items()}

# BOT CARDS
st.markdown('<div class="section-title">Bot Performance</div>', unsafe_allow_html=True)
cols = st.columns(len(BOT_TABS))
for i, (bot_name, df) in enumerate(all_data.items()):
    stats = calc_stats(df)
    color = BOT_COLORS[bot_name]
    currency = '£' if 'Live' in bot_name else '$'
    streak_str = f"{'🔥' if stats['streak']>0 else '❄️'} {abs(stats['streak'])}{'W' if stats['streak']>0 else 'L'}" if stats['trades']>0 else "—"
    with cols[i]:
        st.markdown(f"""<div class="metric-card" style="border-top:3px solid {color}">
            <div class="metric-bot-name">{bot_name}</div>
            <div class="metric-stake" style="color:{color}">{BOT_STAKES[bot_name]}</div>
            <div class="metric-wr {wr_cls(stats['wr'])}">{stats['wr']:.1f}%</div>
            <div class="metric-wr-label">Win Rate</div>
            <div class="metric-pnl {pnl_cls(stats['pnl'])}">{currency}{stats['pnl']:+.2f}</div>
            <div class="metric-pnl-label">Total PnL</div>
            <div class="metric-trades">{stats['wins']}W / {stats['losses']}L · {stats['trades']} trades</div>
            <div class="metric-streak">{streak_str}</div>
        </div>""", unsafe_allow_html=True)

st.markdown('<div class="breakeven-bar"><span style="font-weight:600;color:#374151">Breakeven: 52.2% WR</span><span>·</span><span style="color:#059669">▲ Above 58% = target</span><span>·</span><span style="color:#d97706">▲ Above 52.2% = not losing</span><span>·</span><span style="color:#dc2626">▼ Below 52.2% = losing</span></div>', unsafe_allow_html=True)

# PNL CHART
st.markdown('<div class="section-title">Cumulative PnL Over Time</div>', unsafe_allow_html=True)
fig = go.Figure()
for bot_name, df in all_data.items():
    if df.empty: continue
    df_s = df.sort_values('timestamp')
    df_s = df_s.copy()
    df_s['cum_pnl'] = df_s['pnl'].cumsum()
    fig.add_trace(go.Scatter(x=df_s['timestamp'], y=df_s['cum_pnl'], name=bot_name,
        line=dict(color=BOT_COLORS[bot_name], width=2), mode='lines+markers', marker=dict(size=4)))
fig.add_hline(y=0, line_dash="dot", line_color="#e5e7eb")
fig.update_layout(paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(family='Inter', color='#6b7280', size=11),
    legend=dict(bgcolor='#ffffff', bordercolor='#e5e7eb', borderwidth=1),
    xaxis=dict(gridcolor='#f3f4f6', showgrid=True, linecolor='#e5e7eb'),
    yaxis=dict(gridcolor='#f3f4f6', showgrid=True, title="PnL", linecolor='#e5e7eb'),
    height=300, margin=dict(l=0,r=0,t=10,b=0))
st.plotly_chart(fig, use_container_width=True)

# EXPIRY SWEET SPOT
st.markdown('<div class="section-title">Expiry Sweet Spot</div>', unsafe_allow_html=True)
exp_cols = st.columns(len(all_data))
for i, (bot_name, df) in enumerate(all_data.items()):
    with exp_cols[i]:
        st.markdown(f'<div style="font-size:11px;font-weight:600;color:{BOT_COLORS[bot_name]};margin-bottom:6px">{bot_name}</div>', unsafe_allow_html=True)
        if df.empty: st.markdown('<div style="font-size:12px;color:#d1d5db">No data</div>', unsafe_allow_html=True); continue
        rows = []
        for mins in [7,15,20,30,45,60]:
            col = f'win_{mins}min'
            if col not in df.columns: continue
            s = df[df[col].isin(['WIN','LOSS'])]
            if len(s)<5: continue
            wr = (s[col]=='WIN').mean()*100
            rows.append({"Exp":f"{mins}m","WR":f"{wr:.1f}%","n":len(s)})
        if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# SYMBOL BREAKDOWN
st.markdown('<div class="section-title">Symbol Breakdown</div>', unsafe_allow_html=True)
sym_cols = st.columns(len(all_data))
for i, (bot_name, df) in enumerate(all_data.items()):
    with sym_cols[i]:
        st.markdown(f'<div style="font-size:11px;font-weight:600;color:{BOT_COLORS[bot_name]};margin-bottom:6px">{bot_name}</div>', unsafe_allow_html=True)
        if df.empty: st.markdown('<div style="font-size:12px;color:#d1d5db">No data</div>', unsafe_allow_html=True); continue
        rows = []
        for sym, grp in df.groupby('symbol'):
            w=(grp['outcome']=='WIN').sum(); t=len(grp); p=grp['pnl'].sum()
            rows.append({"Sym":sym,"WR":f"{w/t*100:.0f}%","PnL":f"${p:.2f}"})
        if rows: st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# RECENT TRADES
st.markdown('<div class="section-title">Recent Trades</div>', unsafe_allow_html=True)
all_trades = []
for bot_name, df in all_data.items():
    if not df.empty:
        temp = df.head(15).copy(); temp['bot']=bot_name; all_trades.append(temp)
if all_trades:
    combined = pd.concat(all_trades).sort_values('timestamp', ascending=False).head(30)
    st.markdown('<div class="trade-feed">', unsafe_allow_html=True)
    for _, row in combined.iterrows():
        win = row['outcome']=='WIN'
        cls = 'trade-win' if win else 'trade-loss'
        emoji = '✅' if win else '❌'
        currency = '£' if 'Live' in row['bot'] else '$'
        pnl_color = '#059669' if float(row['pnl'])>=0 else '#dc2626'
        prob = f"{row['ml_prob']*100:.0f}%" if row['ml_prob']>0 else "—"
        time_str = pd.to_datetime(row['timestamp']).strftime('%H:%M')
        bot_color = BOT_COLORS.get(row['bot'],'#6b7280')
        st.markdown(f"""<div class="trade-row {cls}">
            <span style="font-size:14px">{emoji}</span>
            <span class="trade-sym">{row['symbol']}</span>
            <span class="trade-dir">{row['direction']}</span>
            <span class="trade-bot" style="color:{bot_color}">{row['bot']}</span>
            <span class="trade-prob">{prob}</span>
            <span class="trade-pnl" style="color:{pnl_color}">{currency}{float(row['pnl']):+.2f}</span>
            <span class="trade-time">{time_str}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align:center;font-size:11px;color:#d1d5db;padding:8px 0">DAWN BOT MONITOR · Breakeven: 52.2% WR · Auto-refreshes every 30s</div>', unsafe_allow_html=True)
st.markdown("<script>setTimeout(function(){window.location.reload();},30000);</script>", unsafe_allow_html=True)
