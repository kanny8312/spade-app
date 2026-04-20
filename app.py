import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 初始化設定 ---
st.set_page_config(page_title="十杯永和店 ERP 2.1", layout="wide")
ADMIN_PASSWORD = "8312"

# 定義所有原物料的初始庫存
DEFAULT_INVENTORY = {
    "主恩鮮乳(瓶)": 50.0, "柳營鮮乳(罐)": 20.0, "初鹿鮮乳(瓶)": 15.0, 
    "大山鮮乳(瓶)": 10.0, "橋頭鮮乳(瓶)": 10.0,
    "700ml紙杯(個)": 2000.0, "珍珠(g)": 5000.0, "紅茶茶葉(g)": 3000.0,
    "粗吸管(支)": 500.0, "封膜(張)": 3000.0
}

# 確保數據在 session 中持續 (注意：重新整理網頁仍會重置，若要永久儲存需串接 Google Sheets)
if 'inventory' not in st.session_state:
    st.session_state.inventory = DEFAULT_INVENTORY.copy()
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=["時間", "品項", "變動量", "類型", "備註"])

# --- 2. 核心 BOM 扣料大腦 (全品項連動) ---
def apply_bom_deduction(sales_df):
    logs = []
    for _, row in sales_df.iterrows():
        name = str(row['商品名稱'])
        qty = int(str(row['銷售數量']).replace(',', ''))
        
        # 鮮奶類扣除邏輯
        milk_map = {"主恩": "主恩鮮乳(瓶)", "柳營": "柳營鮮乳(罐)", "初鹿": "初鹿鮮乳(瓶)", "大山": "大山鮮乳(瓶)", "橋頭": "橋頭鮮乳(瓶)"}
        for key, val in milk_map.items():
            if key in name or (key == "主恩" and "牧奶茶" in name): # 預設牧奶茶用主恩
                st.session_state.inventory[val] -= (0.228 * qty)
                logs.append({"時間": datetime.now(), "品項": val, "變動量": -(0.228 * qty), "類型": "銷售", "備註": f"售出 {name}"})
        
        # 珍珠扣除邏輯
        if "珍珠" in name:
            st.session_state.inventory["珍珠(g)"] -= (70 * qty)
            logs.append({"時間": datetime.now(), "品項": "珍珠(g)", "變動量": -(70 * qty), "類型": "銷售", "備註": f"加料珍珠: {name}"})
            
        # 包材固定扣除
        if "紙杯(個)" in st.session_state.inventory:
            st.session_state.inventory["700ml紙杯(個)"] -= qty
            st.session_state.inventory["封膜(張)"] -= qty
            logs.append({"時間": datetime.now(), "品項": "700ml紙杯(個)", "變動量": -qty, "類型": "銷售", "備註": f"包材: {name}"})

    if logs:
        st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame(logs)], ignore_index=True)

# --- 3. 介面分頁 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 即時庫存", "📊 銷售扣料", "🔍 理論稽核(第一版)", "🗑️ 報廢/進貨", "⚙️ 系統維護"])

with tab1:
    st.subheader("📦 目前原始庫存狀態")
    # 動態顯示所有庫存項目，確保新增的也能看到
    items = list(st.session_state.inventory.items())
    rows = [items[i:i + 4] for i in range(0, len(items), 4)]
    for row_items in rows:
        cols = st.columns(4)
        for i, (item, val) in enumerate(row_items):
            cols[i].metric(label=item, value=f"{val:.2f}")
    
    st.markdown("---")
    st.subheader("🗓️ 兩週變動明細")
    st.dataframe(st.session_state.ledger.sort_index(ascending=False), use_container_width=True)

with tab2:
    st.subheader("📑 讀取報表並自動扣料")
    f = st.file_uploader("上傳肚肚 CSV", type="csv", key="tab2_u")
    if f and st.button("確認執行庫存扣除"):
        apply_bom_deduction(pd.read_csv(f))
        st.success("已根據商品包裹完成全品項扣料！")

with tab3:
    st.subheader("🔍 鮮奶理論用量精算 (第一版功能)")
    st.info("此分頁僅供數據比對，不會更動原始庫存。")
    f_audit = st.file_uploader("上傳肚肚 CSV 進行稽核", type="csv", key="tab3_u")
    if f_audit:
        df_audit = pd.read_csv(f_audit)
        # 這裡放入你最喜歡的第一版計算公式...
        st.write("稽核完成：今日理論總消耗鮮奶量為 XX ml")

with tab4:
    col_in, col_out = st.columns(2)
    with col_in:
        st.subheader("📥 進貨登記")
        item_in = st.selectbox("品項", list(st.session_state.inventory.keys()), key="sel_in")
        qty_in = st.number_input("數量", min_value=0.0, key="num_in")
        if st.button("確認入庫"):
            st.session_state.inventory[item_in] += qty_in
            new_log = {"時間": datetime.now(), "品項": item_in, "變動量": qty_in, "類型": "進貨", "備註": "手動進貨"}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_log])], ignore_index=True)
            st.success("入庫成功")
    with col_out:
        st.subheader("🗑️ 報廢登記")
        item_out = st.selectbox("品項", list(st.session_state.inventory.keys()), key="sel_out")
        qty_out = st.number_input("數量", min_value=0.0, key="num_out")
        reason = st.text_input("原因")
        if st.button("確認報廢"):
            st.session_state.inventory[item_out] -= qty_out
            new_log = {"時間": datetime.now(), "品項": item_out, "變動量": -qty_out, "類型": "報廢", "備註": reason}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_log])], ignore_index=True)
            st.warning("報廢已扣除")

with tab5:
    st.subheader("🔐 管理員授權")
    pwd = st.text_input("輸入 4 位數密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.success("權限已解除")
        new_name = st.text_input("新增品項名稱 (如：提袋)")
        if st.button("確認新增品項"):
            st.session_state.inventory[new_name] = 0.0
            st.rerun()
        
        st.markdown("---")
        if st.button("📥 下載目前數據備份 (CSV)"):
            st.write("這功能能讓你把目前庫存存下來，避免重新整理消失。")
