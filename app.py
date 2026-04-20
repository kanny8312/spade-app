import streamlit as st
import pandas as pd

# --- 1. 系統設定與頁面標題 ---
st.set_page_config(page_title="十杯永和店 - 營運戰情室", layout="centered")
st.title("🥤 十杯永和店 - 營運戰情室")
st.markdown("---")

# --- 2. 鮮奶消耗計算邏輯 (你的專屬 BOM 表大腦) ---
def calc_milk_volume(row):
    name = str(row['商品名稱']) if '商品名稱' in row else ''
    size = str(row['價位名稱']) if '價位名稱' in row else ''
    qty = pd.to_numeric(str(row['銷售數量']).replace(',', ''), errors='coerce')
    if pd.isna(qty): return 0
    
    ml = 0
    if '牧奶茶' in name or '牧奶綠' in name or '純萃鮮奶茶' in name:
        ml = 165 if (size == 'M' or '(M)' in name) else 215
    elif '歐蕾' in name:
        ml = 50 if (size == 'M' or '(M)' in name) else 60
    elif '可可' in name and '雪霜' not in name:
        ml = 100 if (size == 'M' or '(M)' in name) else 130
    elif '鮮奶' in name and '茶' not in name and '奶精' not in name:
        ml = 200
    return qty * ml

# --- 3. 肚肚報表上傳區 ---
st.subheader("📁 第一步：上傳今日肚肚銷售報表")
uploaded_file = st.file_uploader("請拖曳或選擇 CSV 檔案", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['Theo_ml'] = df.apply(calc_milk_volume, axis=1)
    theo_total_ml = df['Theo_ml'].sum()
    
    st.success("✅ 肚肚報表讀取成功！")
    st.metric(label="今日理論鮮奶消耗總量", value=f"{theo_total_ml:,.0f} ml")
    st.markdown("---")
    
    # --- 4. 晚班盤點輸入區 ---
    st.subheader("📋 第二步：輸入打烊盤點數字")
    col1, col2 = st.columns(2)
    
    with col1:
        juen_start = st.number_input("主恩 (今日期初+進貨瓶數)", min_value=0, value=0)
        juen_end = st.number_input("主恩 (今晚剩餘瓶數)", min_value=0, value=0)
    
    # 計算實際消耗與耗損
    if st.button("🚀 執行耗損對撞分析"):
        # 這裡以主恩 940ml 為例，未來可擴充其他品牌
        actual_consume_bottles = juen_start - juen_end
        actual_consume_ml = actual_consume_bottles * 940
        
        diff_ml = actual_consume_ml - theo_total_ml
        loss_rate = (diff_ml / actual_consume_ml) * 100 if actual_consume_ml > 0 else 0
        
        st.markdown("### 📊 今日耗損報告")
        st.metric(label="實際消耗量", value=f"{actual_consume_ml:,.0f} ml", delta=f"{actual_consume_bottles} 瓶")
        
        # 紅綠燈警告系統
        if loss_rate > 10:
            st.error(f"🚨 警告！今日鮮奶耗損率高達 {loss_rate:.2f}%！請立即查核現場報廢狀況！")
        elif loss_rate > 5:
            st.warning(f"⚠️ 注意。今日鮮奶耗損率 {loss_rate:.2f}%，處於邊緣值。")
        else:
            st.success(f"🟢 完美！今日鮮奶耗損率 {loss_rate:.2f}%，控制在標準內。")
