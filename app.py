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
        selected_users = st.multiselect("表示ユーザー", list(USERS.keys()), default=list(USERS.keys()))
        
        # 入力画面へ行くボタン（メモアイコンの代わり）
        if st.button("📝 収支を記録する", use_container_width=True, type="primary"):
            go_to_input()
            st.rerun()

    # DBからデータ取得
    df = pd.read_sql("SELECT * FROM records", CONN)
    
    # 日付型に変換
    if not df.empty:
        df['date_dt'] = pd.to_datetime(df['date_str'])

    # 今月の収支計算
    today = datetime.date.today()
    this_month_str = today.strftime("%Y年%m月")
    
    current_month_balance = 0
    if not df.empty:
        # 今月 かつ 選択されたユーザー のデータを抽出
        mask_month = (df['date_dt'].dt.year == today.year) & (df['date_dt'].dt.month == today.month)
        mask_user = df['user_text'].isin(selected_users)
        df_month = df[mask_month & mask_user]
        
        current_month_balance = df_month['recovery'].sum() - df_month['investment'].sum()

    with col_h1:
        st.subheader(f"{this_month_str} の収支")
        color = "red" if current_month_balance < 0 else "green"
        st.markdown(f"<h1 style='color:{color}; margin-top:-10px;'>¥{current_month_balance:,}</h1>", unsafe_allow_html=True)

    # --- カレンダーエリア ---
    events = []
    if not df.empty:
        # 選択されたユーザーのデータのみカレンダーに表示
        df_calendar = df[df['user_text'].isin(selected_users)]
        
        for index, row in df_calendar.iterrows():
            balance = row['recovery'] - row['investment']
            title_text = f"¥{balance:,}" 
            if balance > 0: title_text = f"+¥{balance:,}"
            
            events.append({
                "title": f"{row['user_text'][0]} {title_text}", # 名前の頭文字+金額
                "start": row['date_str'],
                "backgroundColor": USERS.get(row['user_text'], "#888"),
                "borderColor": "transparent",
                "extendedProps": {"id": row['id']}
            })

    # カレンダー設定（日本語化）
    calendar_options = {
        "locale": "ja",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": ""
        },
        "initialDate": st.session_state.selected_date,
        "selectable": True, # 日付を選択可能に
    }

    # カレンダー表示
    calendar_event = calendar(events=events, options=calendar_options, key="main_calendar")

    # カレンダー操作時の処理
    if calendar_event.get("dateClick"):
        st.session_state.selected_date = calendar_event["dateClick"]["date"]
        st.rerun() # リロードして下部の表示を更新

    # --- 画面下部：選択した日の詳細リスト ---
    st.write("---")
    st.subheader(f"📅 {st.session_state.selected_date} の記録")

    if not df.empty:
        # 選択された日 かつ 選択されたユーザー
        mask_date = df['date_str'] == st.session_state.selected_date
        mask_user = df['user_text'].isin(selected_users)
        df_day = df[mask_date & mask_user]

        if df_day.empty:
            st.info("この日の記録はありません。右上の「📝 収支を記録する」ボタンから入力してください。")
        else:
            # カラム形式でリスト表示
            for index, row in df_day.iterrows():
                balance = row['recovery'] - row['investment']
                bg_color = USERS.get(row['user_text'], "#eee")
                
                with st.container():
                    # カード風の表示
                    c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
                    with c1:
                        # 行ごとに違うID（key）を持たせることで解決します
                        st.color_picker("", bg_color, disabled=True, label_visibility="collapsed", key=f"color_{row['id']}")
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
    st.button("🔙 カレンダーに戻る", on_click=go_to_calendar)
    st.title("📝 収支の入力")
    
    st.info(f"日付: {st.session_state.selected_date} のデータを入力します")

    with st.form("entry_form"):
        # 日付は選択した日を初期値に
        date_val = datetime.date.fromisoformat(st.session_state.selected_date)
        input_date = st.date_input("日付", date_val)
        
        input_user = st.selectbox("記録するユーザー", list(USERS.keys()))
        
        c1, c2 = st.columns(2)
        with c1:
            input_store = st.text_input("店舗名")
            input_inv = st.number_input("投資額 (円)", step=1000)
        with c2:
            input_machine = st.text_input("機種名")
            input_rec = st.number_input("回収額 (円)", step=1000)
            
        input_memo = st.text_area("メモ")
        
        submitted = st.form_submit_button("保存して戻る", type="primary")
        
        if submitted:
            # DB保存
            C.execute('''
                INSERT INTO records (user_text, date_str, store_text, machine_text, investment, recovery, memo_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (input_user, input_date.isoformat(), input_store, input_machine, input_inv, input_rec, input_memo))
            CONN.commit()
            
            # カレンダーに戻る
            st.success("保存しました")
            st.session_state.selected_date = input_date.isoformat() # 保存した日付を選択状態に
            go_to_input() # リロード用
            go_to_calendar() # ページ戻し用
            st.rerun()
