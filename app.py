import streamlit as st
from streamlit_calendar import calendar
import pandas as pd
import sqlite3
import datetime

# --- 1. 設定と準備 ---
st.set_page_config(page_title="チーム収支管理", layout="wide")

# データベース接続
CONN = sqlite3.connect('kaikei.db', check_same_thread=False)
C = CONN.cursor()
C.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_text TEXT,
        date_str TEXT,
        store_text TEXT,
        machine_text TEXT,
        investment INTEGER,
        recovery INTEGER,
        memo_text TEXT
    )
''')
CONN.commit()

# ユーザー設定
USERS = {
    "ユーザーA": "#FF6B6B", # 赤
    "ユーザーB": "#4ECDC4", # 青緑
    "ユーザーC": "#FFE66D", # 黄
}

# --- セッション状態の管理（画面遷移用） ---
if 'page' not in st.session_state:
    st.session_state.page = 'calendar' # 初期はカレンダー
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.date.today().isoformat()

# --- 画面切り替え関数 ---
def go_to_input():
    st.session_state.page = 'input'

def go_to_calendar():
    st.session_state.page = 'calendar'

# ==========================================
#  メイン画面（カレンダー）
# ==========================================
if st.session_state.page == 'calendar':
    
    # --- ヘッダーエリア (今月の収支とユーザー選択) ---
    col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
    
    # ユーザー選択（重ね合わせ）
    with col_h3:
        # デフォルトは全員選択
        selected_users = st.multise
