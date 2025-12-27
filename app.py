import streamlit as st
from streamlit_calendar import calendar
import pandas as pd
import sqlite3
import datetime

# --- 1. 設定と準備 ---
st.set_page_config(page_title="チーム収支管理", layout="wide")

# データベースへの接続（なければ作る）
CONN = sqlite3.connect('kaikei.db', check_same_thread=False)
C = CONN.cursor()

# テーブル作成（初回のみ実行される）
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

# ユーザー設定（名前とカレンダーの色）
USERS = {
    "ユーザーA": "#FF6B6B", # 赤系
    "ユーザーB": "#4ECDC4", # 青緑系
    "ユーザーC": "#FFE66D", # 黄色系
}

# --- 2. サイドバー（入力フォーム） ---
st.sidebar.title("💰 収支入力")

# 誰の記録か選ぶ
selected_user = st.sidebar.selectbox("記録者を選択", list(USERS.keys()))

with st.sidebar.form("entry_form", clear_on_submit=True):
    date_input = st.date_input("日付", datetime.date.today())
    store_input = st.text_input("店舗名")
    machine_input = st.text_input("機種名")
    
    # 金額入力
    col1, col2 = st.columns(2)
    with col1:
        inv_input = st.number_input("投資額 (円)", min_value=0, step=1000)
    with col2:
        rec_input = st.number_input("回収額 (円)", min_value=0, step=1000)
        
    memo_input = st.text_area("メモ")
    
    submitted = st.form_submit_button("保存する")

    if submitted:
        # DBに保存
        C.execute('''
            INSERT INTO records (user_text, date_str, store_text, machine_text, investment, recovery, memo_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (selected_user, date_input, store_input, machine_input, inv_input, rec_input, memo_input))
        CONN.commit()
        st.success("保存しました！")

# --- 3. メイン画面（カレンダー表示） ---
st.title("📅 チーム収支カレンダー")

# DBからデータを全取得
df = pd.read_sql("SELECT * FROM records", CONN)

# カレンダー用のイベントデータリストを作成
events = []

if not df.empty:
    for index, row in df.iterrows():
        # 収支計算
        balance = row['recovery'] - row['investment']
        
        # 表示テキスト（プラスなら+をつける）
        title_text = f"¥{balance:,}" 
        if balance > 0:
            title_text = f"+¥{balance:,}"

        # カレンダー用データ作成
        event = {
            "title": f"{row['user_text']}: {title_text}",
            "start": row['date_str'],
            "backgroundColor": USERS.get(row['user_text'], "#888888"), # ユーザーごとの色
            "borderColor": USERS.get(row['user_text'], "#888888"),
            # クリックした時に詳細を表示するためのデータ
            "extendedProps": {
                "store": row['store_text'],
                "machine": row['machine_text'],
                "memo": row['memo_text'],
                "investment": row['investment'],
                "recovery": row['recovery']
            }
        }
        events.append(event)

# カレンダーの設定
calendar_options = {
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,listMonth"
    },
    "initialView": "dayGridMonth",
}

# カレンダー表示
calendar_event = calendar(events=events, options=calendar_options)

# --- 4. 詳細表示（カレンダーをクリックした時） ---
if calendar_event.get("eventClick"):
    clicked_data = calendar_event["eventClick"]["event"]
    props = clicked_data["extendedProps"]
    
    st.write("---")
    st.subheader(f"🔍 {clicked_data['title']} の詳細")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    col_d1.metric("店舗", props["store"])
    col_d1.metric("機種", props["machine"])
    
    col_d2.metric("投資", f"¥{props['investment']:,}")
    col_d2.metric("回収", f"¥{props['recovery']:,}")
    
    balance = props['recovery'] - props['investment']
    col_d3.metric("収支", f"¥{balance:,}", delta=f"{balance:,}円")
    
    st.info(f"メモ: {props['memo']}")

# 合計データの表示（おまけ）
st.write("---")
if not df.empty:
    total_inv = df['investment'].sum()
    total_rec = df['recovery'].sum()
    total_bal = total_rec - total_inv
    
    st.subheader("📊 全体合計")
    m1, m2, m3 = st.columns(3)
    m1.metric("総投資", f"¥{total_inv:,}")
    m2.metric("総回収", f"¥{total_rec:,}")
    m3.metric("総収支", f"¥{total_bal:,}", delta=f"{total_bal:,}円")