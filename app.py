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

# ── 顏色選盤（9 種）──────────────────────────────────────────────
COLOR_OPTIONS = {
    "🔵 藍色":  "#4F8EF7",
    "🟢 綠色":  "#27AE60",
    "🟡 黃色":  "#F39C12",
    "🟠 橘色":  "#E67E22",
    "🔴 紅色":  "#E74C3C",
    "🟣 紫色":  "#9B59B6",
    "🩷 粉紅":  "#E91E8C",
    "🩵 天藍":  "#1ABC9C",
    "⬛ 深灰":  "#7F8C8D",
}
COLOR_LABELS  = list(COLOR_OPTIONS.keys())
COLOR_VALUES  = list(COLOR_OPTIONS.values())

COLUMNS = [
    "case_id", "vendor", "vendor_color", "contact_person",
    "assignee", "assignee_color",
    "project_name", "project_type", "start_date", "deadline",
    "deposit_amount", "deposit_status",
    "final_amount",  "final_status",
    "total_amount",  "case_status",
    "source_url", "output_url",
    "labor_year", "notes", "created_at", "updated_at"
]

# ── helpers ──────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype=str).fillna("")
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_data(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv(DATA_FILE, index=False)

def calc_total(dep, fin):
    try:
        return (float(dep) if dep else 0) + (float(fin) if fin else 0)
    except Exception:
        return 0

def get_prev_color(df, name_col, color_col, name):
    """回傳該名字上次使用的顏色，找不到就回傳預設第一個。"""
    if name and not df.empty:
        hits = df[df[name_col] == name]
        if not hits.empty:
            c = hits.iloc[-1][color_col]
            if c in COLOR_VALUES:
                return c
    return COLOR_VALUES[0]

def badge(text, bg):
    """彩色圓角標籤 HTML"""
    if not text:
        return ""
    return (
        f'<span style="background:{bg};color:#fff;'
        f'padding:3px 11px;border-radius:20px;'
        f'font-size:0.80em;font-weight:600;white-space:nowrap;">'
        f'{text}</span>'
    )

def val_to_label(val):
    for k, v in COLOR_OPTIONS.items():
        if v == val:
            return k
    return COLOR_LABELS[0]

def color_picker_radio(label, key, default_val):
    """橫向顯示顏色選單，回傳 hex 值"""
    default_label = val_to_label(default_val)
    chosen_label = st.radio(
        label, COLOR_LABELS,
        index=COLOR_LABELS.index(default_label),
        horizontal=True, key=key
    )
    return COLOR_OPTIONS[chosen_label]

def render_table(display_df):
    """把 DataFrame 渲染成有彩色 badge 的 HTML 表格"""
    rows_html = ""
    for _, r in display_df.iterrows():
        vendor_cell   = badge(r.get("廠商",""), r.get("vendor_color","#7F8C8D"))
        assignee_cell = badge(r.get("接案人",""), r.get("assignee_color","#7F8C8D"))
        rows_html += (
            f"<tr>"
            f"<td>{r.get('ID','')}</td>"
            f"<td>{vendor_cell}</td>"
            f"<td>{r.get('案件名稱','')}</td>"
            f"<td>{assignee_cell}</td>"
            f"<td>{r.get('類型','')}</td>"
            f"<td>{r.get('狀態','')}</td>"
            f"<td>{r.get('前金','')}</td>"
            f"<td>{r.get('前金狀態','')}</td>"
            f"<td>{r.get('後金','')}</td>"
            f"<td>{r.get('後金狀態','')}</td>"
            f"<td><b>{r.get('總金額','')}</b></td>"
            f"<td>{r.get('接案日期','')}</td>"
            f"<td>{r.get('截止日期','')}</td>"
            f"</tr>"
        )
    headers = ["ID","廠商","案件名稱","接案人","類型","狀態",
                "前金","前金狀態","後金","後金狀態","總金額","接案日期","截止日期"]
    th = "".join(f"<th>{h}</th>" for h in headers)
    html = f"""
    <style>
    table.case-table {{border-collapse:collapse;width:100%;font-size:0.85em;}}
    table.case-table th {{background:#4F8EF7;color:white;padding:8px 10px;text-align:left;}}
    table.case-table td {{padding:7px 10px;border-bottom:1px solid #eee;vertical-align:middle;}}
    table.case-table tr:hover td {{background:#F7F9FF;}}
    </style>
    <table class="case-table"><thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table>
    """
    st.markdown(html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# Sidebar
# ════════════════════════════════════════════════════════════════════════════
st.sidebar.title("📋 接案管理系統")
page = st.sidebar.radio(
    "選擇功能",
    ["📊 儀表板", "📝 新增案件", "📁 案件列表", "✏️ 編輯案件", "📤 匯出報表", "💰 試算金額"]
)

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

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("總案件數", len(df))
        c2.metric("進行中", len(df[df["case_status"].isin(["尚未開始","製作中","修改中","待審核"])]))
        c3.metric("待收款",  len(df[df["case_status"] == "結案未收款"]))
        c4.metric("總金額",  f"${df['total_amount'].sum():,.0f}")

        st.markdown("---")
        st.subheader("各狀態案件數")
        sc = df["case_status"].value_counts().reset_index()
        sc.columns = ["狀態","數量"]
        sc["狀態"] = sc["狀態"].apply(lambda x: f"{STATUS_COLORS.get(x,'')} {x}")
        st.dataframe(sc, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("近期案件")
        recent = df.sort_values("start_date", ascending=False).head(10).copy()
        recent_display = recent.rename(columns={
            "vendor":"廠商","project_name":"案件名稱","assignee":"接案人",
            "case_status":"狀態","total_amount":"總金額",
            "start_date":"接案日期","deadline":"截止日期"
        })
        render_table(recent_display.assign(
            **{"ID": recent["case_id"],
               "類型": recent["project_type"],
               "前金": recent["deposit_amount"],
               "前金狀態": recent["deposit_status"],
               "後金": recent["final_amount"],
               "後金狀態": recent["final_status"],
               "vendor_color": recent["vendor_color"],
               "assignee_color": recent["assignee_color"]}
        ))

# ════════════════════════════════════════════════════════════════════════════
# 📝 新增案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "📝 新增案件":
    st.title("📝 新增案件")

    # ── 接案人顏色（表單外先選）─────────────────
    st.subheader("接案人")
    a1, a2 = st.columns([2, 3])
    assignee_input = a1.text_input("接案人姓名 *", key="new_assignee")
    default_a_color = get_prev_color(df, "assignee", "assignee_color", assignee_input)
    with a2:
        assignee_color = color_picker_radio("接案人顏色", "new_a_color", default_a_color)
    if assignee_input:
        st.markdown(
            f'預覽：{badge(assignee_input, assignee_color)}',
            unsafe_allow_html=True
        )

    # ── 廠商顏色（表單外先選）─────────────────
    st.subheader("廠商")
    v1, v2 = st.columns([2, 3])
    vendor_input = v1.text_input("廠商名稱 *", key="new_vendor")
    default_v_color = get_prev_color(df, "vendor", "vendor_color", vendor_input)
    with v2:
        vendor_color = color_picker_radio("廠商顏色", "new_v_color", default_v_color)
    if vendor_input:
        st.markdown(
            f'預覽：{badge(vendor_input, vendor_color)}',
            unsafe_allow_html=True
        )

    st.markdown("---")

    with st.form("add_form", clear_on_submit=True):
        st.subheader("基本資訊")
        f1, f2, f3 = st.columns(3)
        contact      = f1.text_input("聯絡窗口")
        project_name = f2.text_input("案件名稱 *")
        project_type = f3.selectbox("案件類型", PROJECT_TYPES)

        f4, f5 = st.columns(2)
        start_date   = f4.date_input("接案日期", value=date.today())
        deadline     = f5.date_input("截止日期", value=None)
        case_status  = st.selectbox("案件狀態", CASE_STATUSES)

        st.subheader("金額")
        m1, m2, m3, m4 = st.columns(4)
        deposit_amount = m1.number_input("前金金額", min_value=0, value=0, step=100)
        deposit_status = m2.selectbox("前金狀態", DEPOSIT_STATUSES)
        final_amount   = m3.number_input("後金金額", min_value=0, value=0, step=100)
        final_status   = m4.selectbox("後金狀態", DEPOSIT_STATUSES)
        total = deposit_amount + final_amount
        st.markdown(f"**總金額：${total:,}**")

        st.subheader("連結與備註")
        source_url = st.text_input("廠商素材來源網址")
        output_url = st.text_input("成品網址")
        labor_year = st.text_input("勞保申報年份", placeholder="例如：2025")
        notes      = st.text_area("備註")

        submitted = st.form_submit_button("✅ 新增案件", type="primary", use_container_width=True)

    if submitted:
        if not vendor_input or not project_name or not assignee_input:
            st.error("請填寫廠商名稱、案件名稱與接案人。")
        else:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_row = {
                "case_id": str(uuid.uuid4())[:8],
                "vendor": vendor_input, "vendor_color": vendor_color,
                "contact_person": contact,
                "assignee": assignee_input, "assignee_color": assignee_color,
                "project_name": project_name, "project_type": project_type,
                "start_date": str(start_date),
                "deadline": str(deadline) if deadline else "",
                "deposit_amount": str(deposit_amount), "deposit_status": deposit_status,
                "final_amount":   str(final_amount),   "final_status":   final_status,
                "total_amount": str(total), "case_status": case_status,
                "source_url": source_url, "output_url": output_url,
                "labor_year": labor_year, "notes": notes,
                "created_at": now, "updated_at": now,
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
            filter_vendor   = fc1.text_input("廠商名稱（模糊）")
            filter_assignee = fc2.text_input("接案人（模糊）")
            filter_status   = fc3.multiselect("案件狀態", CASE_STATUSES)

        filtered = df.copy()
        if filter_vendor:
            filtered = filtered[filtered["vendor"].str.contains(filter_vendor, na=False)]
        if filter_assignee:
            filtered = filtered[filtered["assignee"].str.contains(filter_assignee, na=False)]
        if filter_status:
            filtered = filtered[filtered["case_status"].isin(filter_status)]

        st.markdown(f"共 **{len(filtered)}** 筆案件")

        display = filtered.rename(columns={
            "vendor":"廠商","project_name":"案件名稱","assignee":"接案人",
            "project_type":"類型","case_status":"狀態",
            "deposit_amount":"前金","deposit_status":"前金狀態",
            "final_amount":"後金","final_status":"後金狀態",
            "total_amount":"總金額","start_date":"接案日期","deadline":"截止日期"
        }).assign(ID=filtered["case_id"])

        render_table(display)

# ════════════════════════════════════════════════════════════════════════════
# ✏️ 編輯案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "✏️ 編輯案件":
    st.title("✏️ 編輯案件")

    if df.empty:
        st.info("尚無案件資料。")
    else:
        options = df.apply(
            lambda r: f"[{r['case_id']}] {r['vendor']} ── {r['project_name']} ({r['assignee']})", axis=1
        ).tolist()
        selected = st.selectbox("選擇要編輯的案件", options)
        idx = options.index(selected)
        row = df.iloc[idx]

        # ── 接案人顏色（表單外）
        st.subheader("接案人")
        ea1, ea2 = st.columns([2, 3])
        edit_assignee = ea1.text_input("接案人姓名", value=row["assignee"], key="edit_assignee")
        default_ea = row["assignee_color"] if row["assignee_color"] in COLOR_VALUES else COLOR_VALUES[0]
        with ea2:
            edit_assignee_color = color_picker_radio("接案人顏色", "edit_a_color", default_ea)
        st.markdown(f'預覽：{badge(edit_assignee, edit_assignee_color)}', unsafe_allow_html=True)

        # ── 廠商顏色（表單外）
        st.subheader("廠商")
        ev1, ev2 = st.columns([2, 3])
        edit_vendor = ev1.text_input("廠商名稱", value=row["vendor"], key="edit_vendor")
        default_ev = row["vendor_color"] if row["vendor_color"] in COLOR_VALUES else COLOR_VALUES[0]
        with ev2:
            edit_vendor_color = color_picker_radio("廠商顏色", "edit_v_color", default_ev)
        st.markdown(f'預覽：{badge(edit_vendor, edit_vendor_color)}', unsafe_allow_html=True)

        st.markdown("---")

        with st.form("edit_form"):
            st.subheader("基本資訊")
            ef1, ef2, ef3 = st.columns(3)
            contact      = ef1.text_input("聯絡窗口", value=row["contact_person"])
            project_name = ef2.text_input("案件名稱", value=row["project_name"])
            project_type = ef3.selectbox("案件類型", PROJECT_TYPES,
                index=PROJECT_TYPES.index(row["project_type"]) if row["project_type"] in PROJECT_TYPES else 0)

            eg1, eg2 = st.columns(2)
            start_date  = eg1.text_input("接案日期", value=row["start_date"])
            deadline    = eg2.text_input("截止日期", value=row["deadline"])
            case_status = st.selectbox("案件狀態", CASE_STATUSES,
                index=CASE_STATUSES.index(row["case_status"]) if row["case_status"] in CASE_STATUSES else 0)

            st.subheader("金額")
            em1, em2, em3, em4 = st.columns(4)
            deposit_amount = em1.text_input("前金金額", value=row["deposit_amount"])
            deposit_status = em2.selectbox("前金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["deposit_status"]) if row["deposit_status"] in DEPOSIT_STATUSES else 0)
            final_amount   = em3.text_input("後金金額", value=row["final_amount"])
            final_status   = em4.selectbox("後金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["final_status"]) if row["final_status"] in DEPOSIT_STATUSES else 0)

            st.subheader("連結與備註")
            source_url = st.text_input("廠商素材來源網址", value=row["source_url"])
            output_url = st.text_input("成品網址", value=row["output_url"])
            labor_year = st.text_input("勞保申報年份", value=row["labor_year"])
            notes      = st.text_area("備註", value=row["notes"])

            col_save, col_del = st.columns([3, 1])
            save_btn = col_save.form_submit_button("💾 儲存變更", type="primary", use_container_width=True)
            del_btn  = col_del.form_submit_button("🗑️ 刪除案件", use_container_width=True)

        if save_btn:
            total = calc_total(deposit_amount, final_amount)
            updates = {
                "vendor": edit_vendor, "vendor_color": edit_vendor_color,
                "contact_person": contact,
                "assignee": edit_assignee, "assignee_color": edit_assignee_color,
                "project_name": project_name, "project_type": project_type,
                "case_status": case_status, "start_date": start_date, "deadline": deadline,
                "deposit_amount": deposit_amount, "deposit_status": deposit_status,
                "final_amount": final_amount, "final_status": final_status,
                "total_amount": str(total),
                "source_url": source_url, "output_url": output_url,
                "labor_year": labor_year, "notes": notes,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            for k, v in updates.items():
                df.at[idx, k] = v
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
        exp_vendor   = ec1.text_input("廠商名稱（留空=全部）")
        exp_assignee = ec2.text_input("接案人（留空=全部）")
        exp_status   = ec3.multiselect("案件狀態（留空=全部）", CASE_STATUSES)

        ec4, ec5 = st.columns(2)
        start_filter = ec4.text_input("接案日期 起（YYYY-MM-DD）")
        end_filter   = ec5.text_input("接案日期 迄（YYYY-MM-DD）")
        exp_year     = st.text_input("勞保申報年份（留空=不篩選）")

        filtered = df.copy()
        if exp_vendor:   filtered = filtered[filtered["vendor"].str.contains(exp_vendor, na=False)]
        if exp_assignee: filtered = filtered[filtered["assignee"].str.contains(exp_assignee, na=False)]
        if exp_status:   filtered = filtered[filtered["case_status"].isin(exp_status)]
        if start_filter: filtered = filtered[filtered["start_date"] >= start_filter]
        if end_filter:   filtered = filtered[filtered["start_date"] <= end_filter]
        if exp_year:     filtered = filtered[filtered["labor_year"] == exp_year]

        st.markdown(f"篩選結果：**{len(filtered)}** 筆")
        if not filtered.empty:
            total_num = pd.to_numeric(filtered["total_amount"], errors="coerce").fillna(0)
            st.metric("篩選結果總金額", f"${total_num.sum():,.0f}")

        export_df = filtered[[
            "vendor","contact_person","assignee","project_name","project_type",
            "case_status","start_date","deadline",
            "deposit_amount","deposit_status","final_amount","final_status","total_amount",
            "source_url","output_url","labor_year","notes","created_at","updated_at"
        ]].copy()
        export_df.columns = [
            "廠商","聯絡窗口","接案人","案件名稱","類型",
            "狀態","接案日期","截止日期",
            "前金","前金狀態","後金","後金狀態","總金額",
            "素材網址","成品網址","勞保申報年份","備註","建立時間","最後更新"
        ]

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="案件明細")
        buf.seek(0)

        st.download_button(
            label="📥 下載 Excel 報表",
            data=buf,
            file_name=f"案件報表_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True, type="primary"
        )

# ════════════════════════════════════════════════════════════════════════════
# 💰 試算金額
# ════════════════════════════════════════════════════════════════════════════
elif page == "💰 試算金額":
    st.title("💰 試算金額")
    st.markdown("快速試算，不會儲存資料。")

    st.subheader("基本試算")
    tc1, tc2 = st.columns(2)
    t_deposit = tc1.number_input("前金金額", min_value=0, value=0, step=100, key="t_dep")
    t_final   = tc2.number_input("後金金額", min_value=0, value=0, step=100, key="t_fin")
    t_total   = t_deposit + t_final

    r1, r2, r3 = st.columns(3)
    r1.metric("前金",  f"${t_deposit:,}")
    r2.metric("後金",  f"${t_final:,}")
    r3.metric("總金額", f"${t_total:,}")

    st.markdown("---")
    st.subheader("扣除費用試算")

    fee_cols = st.columns(3)
    fee1_name = fee_cols[0].text_input("費用項目 1", value="平台手續費")
    fee1_rate = fee_cols[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5, key="f1r")
    fee1_amt  = t_total * fee1_rate / 100
    fee_cols[2].metric(fee1_name, f"-${fee1_amt:,.0f}")

    fee2_cols = st.columns(3)
    fee2_name = fee2_cols[0].text_input("費用項目 2", value="所得稅預扣")
    fee2_rate = fee2_cols[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="f2r")
    fee2_amt  = t_total * fee2_rate / 100
    fee2_cols[2].metric(fee2_name, f"-${fee2_amt:,.0f}")

    st.markdown("---")
    net = t_total - fee1_amt - fee2_amt
    st.markdown(f"### 實拿金額：**${net:,.0f}**")

    st.markdown("---")
    st.subheader("多案件加總試算")
    multi_input = st.text_area("金額清單（每行一筆）", placeholder="5000\n8000\n12000")
    if multi_input:
        try:
            amounts = [float(x.strip()) for x in multi_input.strip().splitlines() if x.strip()]
            mc1, mc2 = st.columns(2)
            mc1.metric("案件數", len(amounts))
            mc2.metric("合計",  f"${sum(amounts):,.0f}")
        except ValueError:
            st.error("請確認每行只輸入數字。")
