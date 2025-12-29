import streamlit as st
from streamlit_calendar import calendar
import pandas as pd
import datetime
from sqlalchemy import text

# --- 1. 設定と準備 ---
st.set_page_config(page_title="チーム収支管理", layout="wide")

# Supabase(PostgreSQL)への接続
conn = st.connection("supabase", type="sql")

# テーブル作成
with conn.session as s:
    s.execute(text('''
        CREATE TABLE IF NOT EXISTS records (
            id SERIAL PRIMARY KEY,
            user_text TEXT,
            date_str TEXT,
            store_text TEXT,
            machine_text TEXT,
            investment INTEGER,
            recovery INTEGER,
            memo_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    '''))
    s.commit()

# ユーザー設定
USER_MAPPING = {
    "your_email@gmail.com": "ユーザーA",
    "friend1@gmail.com": "ユーザーB",
    "friend2@gmail.com": "ユーザーC",
}
USER_COLORS = {
    "ユーザーA": "#FF6B6B", 
    "ユーザーB": "#4ECDC4", 
    "ユーザーC": "#FFE66D", 
}

# --- 2. ユーザー自動判定 ---
current_email = None
try:
    if hasattr(st, "experimental_user"):
        current_email = st.experimental_user.email
except Exception:
    pass

current_user_name = USER_MAPPING.get(current_email)
if not current_user_name:
    with st.sidebar:
        st.caption("Test Mode")
        current_user_name = st.selectbox("ユーザー選択", list(USER_MAPPING.values()))

# --- 3. セッション状態 ---
if 'page' not in st.session_state:
    st.session_state.page = 'calendar'
if 'selected_date' not in st.session_state:
    st.session_state.selected_date = datetime.date.today().isoformat()

# ★ここが修正ポイント：カレンダー再描画用のカウンターを用意
if 'calendar_version' not in st.session_state:
    st.session_state.calendar_version = 0

def go_to_input():
    st.session_state.page = 'input'

def go_to_calendar():
    # カレンダーに戻る時にカウンターを増やして、強制的にリフレッシュさせる
    st.session_state.calendar_version += 1
    st.session_state.page = 'calendar'

# ==========================================
#  メイン画面（カレンダー）
# ==========================================
if st.session_state.page == 'calendar':
    
    # データの取得
    df = conn.query("SELECT * FROM records", ttl=0)
    
    col_h1, col_h2, col_h3 = st.columns([2, 2, 1])
    
    with col_h3:
        all_users = list(USER_MAPPING.values())
        selected_users = st.multiselect("表示ユーザー", all_users, default=all_users)
        
        if st.button("📝 収支を記録する", use_container_width=True, type="primary"):
            go_to_input()
            st.rerun()

    today = datetime.date.today()
    this_month_str = today.strftime("%Y年%m月")
    current_month_balance = 0
    
    if not df.empty:
        df['date_dt'] = pd.to_datetime(df['date_str'])
        mask_month = (df['date_dt'].dt.year == today.year) & (df['date_dt'].dt.month == today.month)
        mask_user = df['user_text'].isin(selected_users)
        df_month = df[mask_month & mask_user]
        if not df_month.empty:
            current_month_balance = df_month['recovery'].sum() - df_month['investment'].sum()

    with col_h1:
        st.subheader(f"{this_month_str} の収支")
        color = "red" if current_month_balance < 0 else "green"
        st.markdown(f"<h1 style='color:{color}; margin-top:-10px;'>¥{current_month_balance:,}</h1>", unsafe_allow_html=True)
        if current_email:
            st.caption(f"ログイン中: {current_user_name}")

    events = []
    if not df.empty:
        df_calendar = df[df['user_text'].isin(selected_users)]
        for index, row in df_calendar.iterrows():
            balance = row['recovery'] - row['investment']
            title_text = f"¥{balance:,}" 
            if balance > 0: title_text = f"+¥{balance:,}"
            
            events.append({
                "title": f"{row['user_text'][0]} {title_text}",
                "start": row['date_str'],
                "backgroundColor": USER_COLORS.get(row['user_text'], "#888"),
                "borderColor": "transparent",
                "extendedProps": {"id": row['id']}
            })

    calendar_options = {
        "locale": "ja",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
        "initialDate": st.session_state.selected_date,
        "selectable": True,
    }

    # ★ここが修正ポイント：時刻ではなく、制御されたバージョン番号を使う
    calendar_event = calendar(
        events=events, 
        options=calendar_options, 
        key=f"cal_v{st.session_state.calendar_version}"
    )

    if calendar_event.get("dateClick"):
        st.session_state.selected_date = calendar_event["dateClick"]["date"]
        # ↓ 日付を変えるたびに画面全体を強制リフレッシュするフラグを追加
        st.session_state.calendar_version += 1
        st.rerun()

    st.write("---")
    st.subheader(f"📅 {st.session_state.selected_date} の記録")

    if not df.empty:
        mask_date = df['date_str'] == st.session_state.selected_date
        mask_user = df['user_text'].isin(selected_users)
        df_day = df[mask_date & mask_user]

        if df_day.empty:
            st.info("この日の記録はありません。")
        else:
            for index, row in df_day.iterrows():
                balance = row['recovery'] - row['investment']
                bg_color = USER_COLORS.get(row['user_text'], "#eee")
                
                with st.container():
                    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
                    with c1:
                        st.color_picker("", bg_color, disabled=True, label_visibility="collapsed", key=f"col_{row['id']}")
                        st.caption(row['user_text'])
                    with c2:
                        st.write(f"**{row['store_text']}**")
                        st.write(f"🎰 {row['machine_text']}")
                    with c3:
                        st.write(f"投資: ¥{row['investment']:,}")
                        st.write(f"回収: ¥{row['recovery']:,}")
                    with c4:
                        st.metric("収支", f"¥{balance:,}")
                    if row['memo_text']:
                        st.caption(f"📝 {row['memo_text']}")
                    st.divider()

# ==========================================
#  入力画面
# ==========================================
elif st.session_state.page == 'input':
    # 戻るボタンを押した時もリフレッシュする
    st.button("🔙 カレンダーに戻る", on_click=go_to_calendar)
    st.title("📝 収支の入力")
    st.info(f"記録者: **{current_user_name}** として保存します")

    with st.form("entry_form"):
        date_val = datetime.date.fromisoformat(st.session_state.selected_date)
        input_date = st.date_input("日付", date_val)
        
        user_options = list(USER_MAPPING.values())
        try:
            default_index = user_options.index(current_user_name)
        except:
            default_index = 0
        input_user = st.selectbox("記録するユーザー", user_options, index=default_index)
        
        c1, c2 = st.columns(2)
        with c1:
            input_store = st.text_input("店舗名")
            input_inv = st.number_input("投資額 (円)", step=1000)
        with c2:
            input_machine = st.text_input("機種名")
            input_rec = st.number_input("回収額 (円)", step=1000)
        input_memo = st.text_area("メモ")
        
        submitted = st.form_submit_button("Supabaseに保存", type="primary")
        
        if submitted:
            with conn.session as s:
                s.execute(
                    text("""
                        INSERT INTO records (user_text, date_str, store_text, machine_text, investment, recovery, memo_text)
                        VALUES (:u, :d, :s, :m, :i, :r, :me)
                    """),
                    {
                        "u": input_user, "d": input_date.isoformat(), "s": input_store,
                        "m": input_machine, "i": input_inv, "r": input_rec, "me": input_memo
                    }
                )
                s.commit()
            
            st.success("保存しました！")
            st.session_state.selected_date = input_date.isoformat()
            
            # 保存時にバージョンを上げて、カレンダーを確実に再描画させる
            st.session_state.calendar_version += 1
            
            go_to_input()
            go_to_calendar()
            st.rerun()
