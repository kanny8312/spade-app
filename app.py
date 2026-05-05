import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import uuid
import io

st.set_page_config(page_title="接案管理系統", page_icon="📋", layout="wide")

DATA_FILE = "data/cases.csv"

CASE_STATUSES = ["尚未開始", "製作中", "修改中", "待審核", "結案未收款", "結案已收款", "勞保待申請", "勞保已申請"]
PROJECT_TYPES = ["設計", "影片", "文案", "網頁", "其他"]
DEPOSIT_STATUSES = ["未收", "已收"]

STATUS_COLORS = {
    "尚未開始": "⚪",
    "製作中": "🔵",
    "修改中": "🟡",
    "待審核": "🟠",
    "結案未收款": "🔴",
    "結案已收款": "🟢",
    "勞保待申請": "🟣",
    "勞保已申請": "✅",
}

COLUMNS = [
    "case_id", "vendor", "contact_person", "assignee", "project_name",
    "project_type", "start_date", "deadline",
    "deposit_amount", "deposit_status",
    "final_amount", "final_status",
    "total_amount", "case_status",
    "source_url", "output_url",
    "labor_year", "notes", "created_at", "updated_at"
]

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_FILE, index=False)

def calc_total(dep, fin):
    try:
        d = float(dep) if dep else 0
        f = float(fin) if fin else 0
        return d + f
    except Exception:
        return 0

# ── Sidebar navigation ──────────────────────────────────────────────────────
st.sidebar.title("📋 接案管理系統")
page = st.sidebar.radio("選擇功能", ["📊 儀表板", "📝 新增案件", "📁 案件列表", "✏️ 編輯案件", "📤 匯出報表", "💰 試算金額"])

df = load_data()

# ════════════════════════════════════════════════════════════════════════════
# 📊 儀表板
# ════════════════════════════════════════════════════════════════════════════
if page == "📊 儀表板":
    st.title("📊 儀表板")

    if df.empty:
        st.info("尚無案件資料，請先新增案件。")
    else:
        df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("總案件數", len(df))
        col2.metric("進行中", len(df[df["case_status"].isin(["尚未開始","製作中","修改中","待審核"])]))
        col3.metric("待收款", len(df[df["case_status"] == "結案未收款"]))
        col4.metric("總金額", f"${df['total_amount'].sum():,.0f}")

        st.markdown("---")
        st.subheader("各狀態案件數")
        status_counts = df["case_status"].value_counts().reset_index()
        status_counts.columns = ["狀態", "數量"]
        status_counts["狀態"] = status_counts["狀態"].apply(lambda x: f"{STATUS_COLORS.get(x,'')} {x}")
        st.dataframe(status_counts, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("近期案件（依接案日期）")
        recent = df.sort_values("start_date", ascending=False).head(10)
        display_cols = ["vendor", "project_name", "assignee", "case_status", "total_amount", "start_date", "deadline"]
        show = recent[[c for c in display_cols if c in recent.columns]].copy()
        show.columns = ["廠商", "案件名稱", "接案人", "狀態", "總金額", "接案日期", "截止日期"][:len(show.columns)]
        st.dataframe(show, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# 📝 新增案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "📝 新增案件":
    st.title("📝 新增案件")

    with st.form("add_form", clear_on_submit=True):
        st.subheader("基本資訊")
        c1, c2, c3 = st.columns(3)
        vendor = c1.text_input("廠商名稱 *")
        contact = c2.text_input("聯絡窗口")
        assignee = c3.text_input("接案人 *")

        c4, c5, c6 = st.columns(3)
        project_name = c4.text_input("案件名稱 *")
        project_type = c5.selectbox("案件類型", PROJECT_TYPES)
        case_status = c6.selectbox("案件狀態", CASE_STATUSES)

        c7, c8 = st.columns(2)
        start_date = c7.date_input("接案日期", value=date.today())
        deadline = c8.date_input("截止日期", value=None)

        st.subheader("金額")
        c9, c10, c11, c12 = st.columns(4)
        deposit_amount = c9.number_input("前金金額", min_value=0, value=0, step=100)
        deposit_status = c10.selectbox("前金狀態", DEPOSIT_STATUSES)
        final_amount = c11.number_input("後金金額", min_value=0, value=0, step=100)
        final_status = c12.selectbox("後金狀態", DEPOSIT_STATUSES)
        total = deposit_amount + final_amount
        st.markdown(f"**總金額：${total:,}**")

        st.subheader("連結與備註")
        source_url = st.text_input("廠商素材來源網址")
        output_url = st.text_input("成品網址")
        labor_year = st.text_input("勞保申報年份", placeholder="例如：2025")
        notes = st.text_area("備註")

        submitted = st.form_submit_button("✅ 新增案件", type="primary", use_container_width=True)

    if submitted:
        if not vendor or not project_name or not assignee:
            st.error("請填寫廠商名稱、案件名稱與接案人。")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = {
                "case_id": str(uuid.uuid4())[:8],
                "vendor": vendor,
                "contact_person": contact,
                "assignee": assignee,
                "project_name": project_name,
                "project_type": project_type,
                "start_date": str(start_date),
                "deadline": str(deadline) if deadline else "",
                "deposit_amount": str(deposit_amount),
                "deposit_status": deposit_status,
                "final_amount": str(final_amount),
                "final_status": final_status,
                "total_amount": str(total),
                "case_status": case_status,
                "source_url": source_url,
                "output_url": output_url,
                "labor_year": labor_year,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success(f"✅ 案件「{project_name}」已新增！")
            st.balloons()

# ════════════════════════════════════════════════════════════════════════════
# 📁 案件列表
# ════════════════════════════════════════════════════════════════════════════
elif page == "📁 案件列表":
    st.title("📁 案件列表")

    if df.empty:
        st.info("尚無案件資料。")
    else:
        with st.expander("🔍 篩選條件", expanded=True):
            fc1, fc2, fc3 = st.columns(3)
            filter_vendor = fc1.text_input("廠商名稱（模糊搜尋）")
            filter_assignee = fc2.text_input("接案人（模糊搜尋）")
            filter_status = fc3.multiselect("案件狀態", CASE_STATUSES)

        filtered = df.copy()
        if filter_vendor:
            filtered = filtered[filtered["vendor"].str.contains(filter_vendor, na=False)]
        if filter_assignee:
            filtered = filtered[filtered["assignee"].str.contains(filter_assignee, na=False)]
        if filter_status:
            filtered = filtered[filtered["case_status"].isin(filter_status)]

        st.markdown(f"共 **{len(filtered)}** 筆案件")

        display = filtered[[
            "case_id", "vendor", "project_name", "assignee", "project_type",
            "case_status", "deposit_amount", "deposit_status",
            "final_amount", "final_status", "total_amount",
            "start_date", "deadline", "source_url", "output_url", "notes"
        ]].copy()
        display.columns = [
            "ID", "廠商", "案件名稱", "接案人", "類型",
            "狀態", "前金", "前金狀態", "後金", "後金狀態", "總金額",
            "接案日期", "截止日期", "素材網址", "成品網址", "備註"
        ]
        display["狀態"] = display["狀態"].apply(lambda x: f"{STATUS_COLORS.get(x,'')} {x}")
        st.dataframe(display, use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════════════════════════
# ✏️ 編輯案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "✏️ 編輯案件":
    st.title("✏️ 編輯案件")

    if df.empty:
        st.info("尚無案件資料。")
    else:
        options = df.apply(lambda r: f"[{r['case_id']}] {r['vendor']} ── {r['project_name']} ({r['assignee']})", axis=1).tolist()
        selected = st.selectbox("選擇要編輯的案件", options)
        idx = options.index(selected)
        row = df.iloc[idx]

        with st.form("edit_form"):
            st.subheader("基本資訊")
            c1, c2, c3 = st.columns(3)
            vendor = c1.text_input("廠商名稱", value=row["vendor"])
            contact = c2.text_input("聯絡窗口", value=row["contact_person"])
            assignee = c3.text_input("接案人", value=row["assignee"])

            c4, c5, c6 = st.columns(3)
            project_name = c4.text_input("案件名稱", value=row["project_name"])
            project_type = c5.selectbox("案件類型", PROJECT_TYPES,
                index=PROJECT_TYPES.index(row["project_type"]) if row["project_type"] in PROJECT_TYPES else 0)
            case_status = c6.selectbox("案件狀態", CASE_STATUSES,
                index=CASE_STATUSES.index(row["case_status"]) if row["case_status"] in CASE_STATUSES else 0)

            c7, c8 = st.columns(2)
            start_date = c7.text_input("接案日期", value=row["start_date"])
            deadline = c8.text_input("截止日期", value=row["deadline"])

            st.subheader("金額")
            c9, c10, c11, c12 = st.columns(4)
            deposit_amount = c9.text_input("前金金額", value=row["deposit_amount"])
            deposit_status = c10.selectbox("前金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["deposit_status"]) if row["deposit_status"] in DEPOSIT_STATUSES else 0)
            final_amount = c11.text_input("後金金額", value=row["final_amount"])
            final_status = c12.selectbox("後金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["final_status"]) if row["final_status"] in DEPOSIT_STATUSES else 0)

            st.subheader("連結與備註")
            source_url = st.text_input("廠商素材來源網址", value=row["source_url"])
            output_url = st.text_input("成品網址", value=row["output_url"])
            labor_year = st.text_input("勞保申報年份", value=row["labor_year"])
            notes = st.text_area("備註", value=row["notes"])

            col_save, col_del = st.columns([3, 1])
            save_btn = col_save.form_submit_button("💾 儲存變更", type="primary", use_container_width=True)
            del_btn = col_del.form_submit_button("🗑️ 刪除案件", use_container_width=True)

        if save_btn:
            total = calc_total(deposit_amount, final_amount)
            df.at[idx, "vendor"] = vendor
            df.at[idx, "contact_person"] = contact
            df.at[idx, "assignee"] = assignee
            df.at[idx, "project_name"] = project_name
            df.at[idx, "project_type"] = project_type
            df.at[idx, "case_status"] = case_status
            df.at[idx, "start_date"] = start_date
            df.at[idx, "deadline"] = deadline
            df.at[idx, "deposit_amount"] = deposit_amount
            df.at[idx, "deposit_status"] = deposit_status
            df.at[idx, "final_amount"] = final_amount
            df.at[idx, "final_status"] = final_status
            df.at[idx, "total_amount"] = str(total)
            df.at[idx, "source_url"] = source_url
            df.at[idx, "output_url"] = output_url
            df.at[idx, "labor_year"] = labor_year
            df.at[idx, "notes"] = notes
            df.at[idx, "updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_data(df)
            st.success("✅ 已儲存！")
            st.rerun()

        if del_btn:
            df = df.drop(index=idx).reset_index(drop=True)
            save_data(df)
            st.success("🗑️ 案件已刪除。")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# 📤 匯出報表
# ════════════════════════════════════════════════════════════════════════════
elif page == "📤 匯出報表":
    st.title("📤 匯出報表")

    if df.empty:
        st.info("尚無案件資料。")
    else:
        st.subheader("篩選條件")
        ec1, ec2, ec3 = st.columns(3)
        exp_vendor = ec1.text_input("廠商名稱（留空=全部）")
        exp_assignee = ec2.text_input("接案人（留空=全部）")
        exp_status = ec3.multiselect("案件狀態（留空=全部）", CASE_STATUSES)

        ec4, ec5 = st.columns(2)
        start_filter = ec4.text_input("接案日期 起（YYYY-MM-DD）")
        end_filter = ec5.text_input("接案日期 迄（YYYY-MM-DD）")

        exp_year = st.text_input("勞保申報年份（留空=不篩選）")

        filtered = df.copy()
        if exp_vendor:
            filtered = filtered[filtered["vendor"].str.contains(exp_vendor, na=False)]
        if exp_assignee:
            filtered = filtered[filtered["assignee"].str.contains(exp_assignee, na=False)]
        if exp_status:
            filtered = filtered[filtered["case_status"].isin(exp_status)]
        if start_filter:
            filtered = filtered[filtered["start_date"] >= start_filter]
        if end_filter:
            filtered = filtered[filtered["start_date"] <= end_filter]
        if exp_year:
            filtered = filtered[filtered["labor_year"] == exp_year]

        st.markdown(f"篩選結果：**{len(filtered)}** 筆")

        export_df = filtered[[
            "vendor", "contact_person", "assignee", "project_name", "project_type",
            "case_status", "start_date", "deadline",
            "deposit_amount", "deposit_status", "final_amount", "final_status", "total_amount",
            "source_url", "output_url", "labor_year", "notes", "created_at", "updated_at"
        ]].copy()
        export_df.columns = [
            "廠商", "聯絡窗口", "接案人", "案件名稱", "類型",
            "狀態", "接案日期", "截止日期",
            "前金", "前金狀態", "後金", "後金狀態", "總金額",
            "素材網址", "成品網址", "勞保申報年份", "備註", "建立時間", "最後更新"
        ]

        if not filtered.empty:
            total_numeric = pd.to_numeric(filtered["total_amount"], errors="coerce").fillna(0)
            st.metric("篩選結果總金額", f"${total_numeric.sum():,.0f}")

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="案件明細")
        buf.seek(0)

        filename = f"案件報表_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        st.download_button(
            label="📥 下載 Excel 報表",
            data=buf,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary"
        )

# ════════════════════════════════════════════════════════════════════════════
# 💰 試算金額
# ════════════════════════════════════════════════════════════════════════════
elif page == "💰 試算金額":
    st.title("💰 試算金額")
    st.markdown("快速試算案件金額，不會儲存資料。")

    st.subheader("基本試算")
    tc1, tc2 = st.columns(2)
    t_deposit = tc1.number_input("前金金額", min_value=0, value=0, step=100, key="t_dep")
    t_final = tc2.number_input("後金金額", min_value=0, value=0, step=100, key="t_fin")
    t_total = t_deposit + t_final

    st.markdown("---")
    r1, r2, r3 = st.columns(3)
    r1.metric("前金", f"${t_deposit:,}")
    r2.metric("後金", f"${t_final:,}")
    r3.metric("總金額", f"${t_total:,}")

    st.markdown("---")
    st.subheader("扣除費用試算")
    st.caption("例如：平台手續費、稅款等")

    fee_cols = st.columns(3)
    fee1_name = fee_cols[0].text_input("費用項目 1", value="平台手續費")
    fee1_rate = fee_cols[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5, key="f1r")
    fee1_amt = t_total * fee1_rate / 100
    fee_cols[2].metric(f"{fee1_name}", f"-${fee1_amt:,.0f}")

    fee2_cols = st.columns(3)
    fee2_name = fee2_cols[0].text_input("費用項目 2", value="所得稅預扣")
    fee2_rate = fee2_cols[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="f2r")
    fee2_amt = t_total * fee2_rate / 100
    fee2_cols[2].metric(f"{fee2_name}", f"-${fee2_amt:,.0f}")

    net = t_total - fee1_amt - fee2_amt
    st.markdown("---")
    st.markdown(f"### 實拿金額：**${net:,.0f}**")

    st.markdown("---")
    st.subheader("多案件加總試算")
    st.caption("輸入多筆金額，以換行分隔")
    multi_input = st.text_area("金額清單（每行一筆）", placeholder="5000\n8000\n12000")
    if multi_input:
        try:
            amounts = [float(x.strip()) for x in multi_input.strip().splitlines() if x.strip()]
            mc1, mc2 = st.columns(2)
            mc1.metric("案件數", len(amounts))
            mc2.metric("合計", f"${sum(amounts):,.0f}")
        except ValueError:
            st.error("請確認每行只輸入數字。")
