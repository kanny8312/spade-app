import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 高規格介面配置 ---
st.set_page_config(page_title="十杯永和店 ERP", layout="wide")
st.title("🛡️ 十杯永和店 - 數位資產管理系統")
st.markdown("---")

# --- 2. 系統初始化 (核心資料結構) ---
# 密碼設定
ADMIN_PASSWORD = "8312"

# 初始化原始庫存 (包含 5 種鮮奶、包材、原物料)
if 'inventory' not in st.session_state:
    st.session_state.inventory = {
        "主恩鮮乳(瓶)": 50.0, "柳營鮮乳(罐)": 20.0, "初鹿鮮乳(瓶)": 15.0, 
        "大山鮮乳(瓶)": 10.0, "橋頭鮮乳(瓶)": 10.0,
        "700ml 紙杯(個)": 2000.0, "封膜(張)": 3000.0, "粗吸管(支)": 500.0,
        "紅茶茶葉(g)": 5000.0, "珍珠(g)": 3000.0, "標籤紙(卷)": 50.0
    }

# 初始化交易帳本 (追蹤所有變動)
if 'ledger' not in st.session_state:
    st.session_state.ledger = pd.DataFrame(columns=["時間", "品項", "變動量", "類型", "備註"])

# --- 3. BOM 包裹扣料邏輯 (定義每一杯飲料用掉什麼) ---
def process_bom_deduction(sales_df):
    logs = []
    for _, row in sales_df.iterrows():
        name = str(row['商品名稱'])
        qty = int(str(row['銷售數量']).replace(',', ''))
        
        # 範例規則：只要包含「牧奶茶」且為 L 杯 (假設默認 L)
        if "牧奶茶" in name:
            # 扣除主恩鮮乳 (215ml 約 0.23 瓶)
            deduct_qty = 0.228 * qty 
            st.session_state.inventory["主恩鮮乳(瓶)"] -= deduct_qty
            st.session_state.inventory["700ml 紙杯(個)"] -= qty
            st.session_state.inventory["封膜(張)"] -= qty
            st.session_state.inventory["紅茶茶葉(g)"] -= (6.6 * qty)
            
            logs.append({"時間": datetime.now(), "品項": "主恩鮮乳(瓶)", "變動量": -deduct_qty, "類型": "銷售", "備註": f"售出 {qty} 杯 {name}"})
            logs.append({"時間": datetime.now(), "品項": "700ml 紙杯(個)", "變動量": -qty, "類型": "銷售", "備註": f"售出 {qty} 杯 {name}"})
            
    if logs:
        st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame(logs)], ignore_index=True)

# --- 4. 功能分頁介面 ---
tab1, tab2, tab3, tab4 = st.tabs(["📦 庫存總覽", "📥 銷售結算", "🗑️ 報廢/進貨登記", "⚙️ 系統維護"])

# --- Tab 1: 庫存總覽 (14天明細) ---
with tab1:
    st.subheader("📦 即時原始庫存")
    # 顯示 5 種牛奶與主要品項
    items = list(st.session_state.inventory.items())
    cols = st.columns(4)
    for idx, (item, val) in enumerate(items):
        cols[idx % 4].metric(label=item, value=f"{val:.2f}")

    st.markdown("---")
    st.subheader("🗓️ 14 天內變動明細")
    # 只顯示最近 14 天的資料
    fourteen_days_ago = datetime.now() - timedelta(days=14)
    display_df = st.session_state.ledger.copy()
    if not display_df.empty:
        display_df['時間'] = pd.to_datetime(display_df['時間'])
        display_df = display_df[display_df['時間'] > fourteen_days_ago]
        st.dataframe(display_df.sort_values("時間", ascending=False), use_container_width=True)
    else:
        st.info("尚無變動紀錄")

# --- Tab 2: 銷售結算 (原本的分支保留) ---
with tab2:
    st.subheader("📊 匯入肚肚報表自動扣料")
    file = st.file_uploader("上傳每日 CSV 報表", type="csv", key="sales_upload")
    if file:
        sales_df = pd.read_csv(file)
        if st.button("確認扣除庫存"):
            process_bom_deduction(sales_df)
            st.success("BOM 包裹扣料完成！庫存已同步更新。")

# --- Tab 3: 報廢與進貨 ---
with tab3:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📥 手動進貨入庫")
        in_item = st.selectbox("進貨品項", list(st.session_state.inventory.keys()), key="in_item")
        in_qty = st.number_input("進貨數量", min_value=0.0, step=1.0)
        if st.button("執行進貨"):
            st.session_state.inventory[in_item] += in_qty
            new_log = {"時間": datetime.now(), "品項": in_item, "變動量": in_qty, "類型": "進貨", "備註": "手動採購入庫"}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_log])], ignore_index=True)
            st.success(f"{in_item} 已增加 {in_qty}")

    with col_b:
        st.subheader("🗑️ 報廢登記 (納入庫存扣除)")
        out_item = st.selectbox("報廢品項", list(st.session_state.inventory.keys()), key="out_item")
        out_qty = st.number_input("報廢數量", min_value=0.0, step=1.0)
        reason = st.text_input("報廢原因", placeholder="例如：過期、煮壞、打翻")
        if st.button("執行報廢"):
            st.session_state.inventory[out_item] -= out_qty
            new_log = {"時間": datetime.now(), "品項": out_item, "變動量": -out_qty, "類型": "報廢", "備註": reason}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_log])], ignore_index=True)
            st.warning(f"{out_item} 已扣除報廢量 {out_qty}")

# --- Tab 4: 系統維護 (密碼鎖與增減品項) ---
with tab4:
    st.subheader("🔐 管理員強制作業")
    pwd = st.text_input("請輸入 4 位數主管密碼", type="password")
    
    if pwd == ADMIN_PASSWORD:
        st.success("密碼正確，已解鎖修改權限")
        
        st.markdown("### 🛠️ 原始庫存強制修正")
        edit_item = st.selectbox("欲修正品項", list(st.session_state.inventory.keys()))
        current_val = st.session_state.inventory[edit_item]
        new_val = st.number_input(f"將 {edit_item} 修正為", value=float(current_val))
        
        if st.button("強制更新庫存"):
            st.session_state.inventory[edit_item] = new_val
            new_log = {"時間": datetime.now(), "品項": edit_item, "變動量": new_val - current_val, "類型": "手動校正", "備註": "管理員密碼強制修改"}
            st.session_state.ledger = pd.concat([st.session_state.ledger, pd.DataFrame([new_log])], ignore_index=True)
            st.success("數值已強制校正")

        st.markdown("---")
        st.markdown("### ➕ 新增/減少系統品項")
        new_item_name = st.text_input("新增品項名稱 (例如：提袋)")
        init_stock = st.number_input("初始庫存量", value=0.0)
        if st.button("新增此品項"):
            st.session_state.inventory[new_item_name] = init_stock
            st.info(f"系統已納入新監控品項：{new_item_name}")
    else:
        if pwd != "":
            st.error("密碼錯誤，無法進行修正")
