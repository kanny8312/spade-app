import streamlit as st
import pandas as pd
from datetime import date, datetime
import uuid
import io
from supabase import create_client

st.set_page_config(page_title="接案管理系統", page_icon="📋", layout="wide")

CASE_STATUSES = ["尚未開始", "製作中", "修改中", "待審核", "結案未收款", "結案已收款", "勞保待申請", "勞保已申請"]
PROJECT_TYPES = ["設計", "影片", "文案", "網頁", "其他"]
DEPOSIT_STATUSES = ["未收", "已收"]

STATUS_COLORS = {
    "尚未開始": "⚪", "製作中": "🔵", "修改中": "🟡", "待審核": "🟠",
    "結案未收款": "🔴", "結案已收款": "🟢", "勞保待申請": "🟣", "勞保已申請": "✅",
}

COLOR_OPTIONS = {
    "🔵 藍色": "#4F8EF7", "🟢 綠色": "#27AE60", "🟡 黃色": "#F39C12",
    "🟠 橘色": "#E67E22", "🔴 紅色": "#E74C3C", "🟣 紫色": "#9B59B6",
    "🩷 粉紅": "#E91E8C", "🩵 天藍": "#1ABC9C", "⬛ 深灰": "#7F8C8D",
}
COLOR_LABELS = list(COLOR_OPTIONS.keys())
COLOR_VALUES = list(COLOR_OPTIONS.values())

# ── Supabase ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def load_data():
    try:
        res = get_client().table("cases").select("*").order("start_date", desc=True).execute()
        if res.data:
            return pd.DataFrame(res.data).fillna("")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"載入資料失敗：{e}")
        return pd.DataFrame()

def insert_case(row: dict):
    get_client().table("cases").insert(row).execute()

def update_case(case_id: str, updates: dict):
    get_client().table("cases").update(updates).eq("case_id", case_id).execute()

def delete_case(case_id: str):
    get_client().table("cases").delete().eq("case_id", case_id).execute()

# ── helpers ───────────────────────────────────────────────────────────────
def calc_total(dep, fin):
    try:
        return (float(dep) if dep else 0) + (float(fin) if fin else 0)
    except Exception:
        return 0

def get_prev_color(df, name_col, color_col, name):
    if name and not df.empty and name_col in df.columns:
        hits = df[df[name_col] == name]
        if not hits.empty and color_col in hits.columns:
            c = hits.iloc[-1][color_col]
            if c in COLOR_VALUES:
                return c
    return COLOR_VALUES[0]

def badge(text, bg):
    if not text:
        return ""
    return (f'<span style="background:{bg};color:#fff;padding:3px 11px;'
            f'border-radius:20px;font-size:0.80em;font-weight:600;white-space:nowrap;">'
            f'{text}</span>')

def val_to_label(val):
    for k, v in COLOR_OPTIONS.items():
        if v == val:
            return k
    return COLOR_LABELS[0]

def color_picker_radio(label, key, default_val):
    default_label = val_to_label(default_val)
    chosen = st.radio(label, COLOR_LABELS,
                      index=COLOR_LABELS.index(default_label),
                      horizontal=True, key=key)
    return COLOR_OPTIONS[chosen]

def render_table(rows):
    if not rows:
        st.info("沒有符合條件的案件。")
        return
    headers = ["ID","廠商","案件名稱","接案人","類型","狀態",
                "前金","前金狀態","後金","後金狀態","總金額","接案日期","截止日期"]
    th = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = ""
    for r in rows:
        rows_html += (
            f"<tr>"
            f"<td>{r.get('case_id','')}</td>"
            f"<td>{badge(r.get('vendor',''), r.get('vendor_color','#7F8C8D'))}</td>"
            f"<td>{r.get('project_name','')}</td>"
            f"<td>{badge(r.get('assignee',''), r.get('assignee_color','#7F8C8D'))}</td>"
            f"<td>{r.get('project_type','')}</td>"
            f"<td>{STATUS_COLORS.get(r.get('case_status',''),'')} {r.get('case_status','')}</td>"
            f"<td>{r.get('deposit_amount','')}</td>"
            f"<td>{r.get('deposit_status','')}</td>"
            f"<td>{r.get('final_amount','')}</td>"
            f"<td>{r.get('final_status','')}</td>"
            f"<td><b>{r.get('total_amount','')}</b></td>"
            f"<td>{r.get('start_date','')}</td>"
            f"<td>{r.get('deadline','')}</td>"
            f"</tr>"
        )
    html = f"""
    <style>
    table.ct{{border-collapse:collapse;width:100%;font-size:0.85em;}}
    table.ct th{{background:#4F8EF7;color:white;padding:8px 10px;text-align:left;}}
    table.ct td{{padding:7px 10px;border-bottom:1px solid #eee;vertical-align:middle;}}
    table.ct tr:hover td{{background:#F7F9FF;}}
    </style>
    <table class="ct"><thead><tr>{th}</tr></thead><tbody>{rows_html}</tbody></table>
    """
    st.markdown(html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# Sidebar
# ════════════════════════════════════════════════════════════════════════════
st.sidebar.title("📋 接案管理系統")
page = st.sidebar.radio("選擇功能", [
    "📊 儀表板", "📝 新增案件", "📁 案件列表",
    "✏️ 編輯案件", "📤 匯出報表", "💰 試算金額"
])

df = load_data()
rows = df.to_dict("records") if not df.empty else []

# ════════════════════════════════════════════════════════════════════════════
# 📊 儀表板
# ════════════════════════════════════════════════════════════════════════════
if page == "📊 儀表板":
    st.title("📊 儀表板")
    if not rows:
        st.info("尚無案件資料，請先新增案件。")
    else:
        total_amt = sum(float(r.get("total_amount") or 0) for r in rows)
        in_progress = [r for r in rows if r.get("case_status") in ["尚未開始","製作中","修改中","待審核"]]
        pending_pay = [r for r in rows if r.get("case_status") == "結案未收款"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("總案件數", len(rows))
        c2.metric("進行中",   len(in_progress))
        c3.metric("待收款",   len(pending_pay))
        c4.metric("總金額",   f"${total_amt:,.0f}")

        st.markdown("---")
        st.subheader("各狀態案件數")
        from collections import Counter
        sc = Counter(r.get("case_status","") for r in rows)
        sc_df = pd.DataFrame(sc.items(), columns=["狀態","數量"])
        sc_df["狀態"] = sc_df["狀態"].apply(lambda x: f"{STATUS_COLORS.get(x,'')} {x}")
        st.dataframe(sc_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("近期案件")
        render_table(rows[:10])

# ════════════════════════════════════════════════════════════════════════════
# 📝 新增案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "📝 新增案件":
    st.title("📝 新增案件")

    st.subheader("接案人")
    a1, a2 = st.columns([2, 3])
    assignee_input = a1.text_input("接案人姓名 *", key="new_assignee")
    default_a = get_prev_color(df, "assignee", "assignee_color", assignee_input)
    with a2:
        assignee_color = color_picker_radio("接案人顏色", "new_a_color", default_a)
    if assignee_input:
        st.markdown(f'預覽：{badge(assignee_input, assignee_color)}', unsafe_allow_html=True)

    st.subheader("廠商")
    v1, v2 = st.columns([2, 3])
    vendor_input = v1.text_input("廠商名稱 *", key="new_vendor")
    default_v = get_prev_color(df, "vendor", "vendor_color", vendor_input)
    with v2:
        vendor_color = color_picker_radio("廠商顏色", "new_v_color", default_v)
    if vendor_input:
        st.markdown(f'預覽：{badge(vendor_input, vendor_color)}', unsafe_allow_html=True)

    st.markdown("---")

    with st.form("add_form", clear_on_submit=True):
        st.subheader("基本資訊")
        f1, f2, f3 = st.columns(3)
        contact      = f1.text_input("聯絡窗口")
        project_name = f2.text_input("案件名稱 *")
        project_type = f3.selectbox("案件類型", PROJECT_TYPES)

        f4, f5 = st.columns(2)
        start_date  = f4.date_input("接案日期", value=date.today())
        deadline    = f5.date_input("截止日期", value=None)
        case_status = st.selectbox("案件狀態", CASE_STATUSES)

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
                "final_amount": str(final_amount), "final_status": final_status,
                "total_amount": str(total), "case_status": case_status,
                "source_url": source_url, "output_url": output_url,
                "labor_year": labor_year, "notes": notes,
                "created_at": now, "updated_at": now,
            }
            insert_case(new_row)
            st.success(f"✅ 案件「{project_name}」已新增！")
            st.cache_resource.clear()
            st.balloons()

# ════════════════════════════════════════════════════════════════════════════
# 📁 案件列表
# ════════════════════════════════════════════════════════════════════════════
elif page == "📁 案件列表":
    st.title("📁 案件列表")
    if not rows:
        st.info("尚無案件資料。")
    else:
        with st.expander("🔍 篩選條件", expanded=True):
            fc1, fc2, fc3 = st.columns(3)
            filter_vendor   = fc1.text_input("廠商名稱（模糊）")
            filter_assignee = fc2.text_input("接案人（模糊）")
            filter_status   = fc3.multiselect("案件狀態", CASE_STATUSES)

        filtered = rows
        if filter_vendor:
            filtered = [r for r in filtered if filter_vendor in r.get("vendor","")]
        if filter_assignee:
            filtered = [r for r in filtered if filter_assignee in r.get("assignee","")]
        if filter_status:
            filtered = [r for r in filtered if r.get("case_status") in filter_status]

        st.markdown(f"共 **{len(filtered)}** 筆案件")
        render_table(filtered)

# ════════════════════════════════════════════════════════════════════════════
# ✏️ 編輯案件
# ════════════════════════════════════════════════════════════════════════════
elif page == "✏️ 編輯案件":
    st.title("✏️ 編輯案件")
    if not rows:
        st.info("尚無案件資料。")
    else:
        options = [f"[{r['case_id']}] {r['vendor']} ── {r['project_name']} ({r['assignee']})" for r in rows]
        selected = st.selectbox("選擇要編輯的案件", options)
        idx = options.index(selected)
        row = rows[idx]

        st.subheader("接案人")
        ea1, ea2 = st.columns([2, 3])
        edit_assignee = ea1.text_input("接案人姓名", value=row.get("assignee",""), key="edit_assignee")
        default_ea = row.get("assignee_color","") if row.get("assignee_color","") in COLOR_VALUES else COLOR_VALUES[0]
        with ea2:
            edit_assignee_color = color_picker_radio("接案人顏色", "edit_a_color", default_ea)
        st.markdown(f'預覽：{badge(edit_assignee, edit_assignee_color)}', unsafe_allow_html=True)

        st.subheader("廠商")
        ev1, ev2 = st.columns([2, 3])
        edit_vendor = ev1.text_input("廠商名稱", value=row.get("vendor",""), key="edit_vendor")
        default_ev = row.get("vendor_color","") if row.get("vendor_color","") in COLOR_VALUES else COLOR_VALUES[0]
        with ev2:
            edit_vendor_color = color_picker_radio("廠商顏色", "edit_v_color", default_ev)
        st.markdown(f'預覽：{badge(edit_vendor, edit_vendor_color)}', unsafe_allow_html=True)

        st.markdown("---")

        with st.form("edit_form"):
            st.subheader("基本資訊")
            ef1, ef2, ef3 = st.columns(3)
            contact      = ef1.text_input("聯絡窗口", value=row.get("contact_person",""))
            project_name = ef2.text_input("案件名稱", value=row.get("project_name",""))
            project_type = ef3.selectbox("案件類型", PROJECT_TYPES,
                index=PROJECT_TYPES.index(row["project_type"]) if row.get("project_type") in PROJECT_TYPES else 0)

            eg1, eg2 = st.columns(2)
            start_date  = eg1.text_input("接案日期", value=row.get("start_date",""))
            deadline    = eg2.text_input("截止日期", value=row.get("deadline",""))
            case_status = st.selectbox("案件狀態", CASE_STATUSES,
                index=CASE_STATUSES.index(row["case_status"]) if row.get("case_status") in CASE_STATUSES else 0)

            st.subheader("金額")
            em1, em2, em3, em4 = st.columns(4)
            deposit_amount = em1.text_input("前金金額", value=row.get("deposit_amount",""))
            deposit_status = em2.selectbox("前金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["deposit_status"]) if row.get("deposit_status") in DEPOSIT_STATUSES else 0)
            final_amount   = em3.text_input("後金金額", value=row.get("final_amount",""))
            final_status   = em4.selectbox("後金狀態", DEPOSIT_STATUSES,
                index=DEPOSIT_STATUSES.index(row["final_status"]) if row.get("final_status") in DEPOSIT_STATUSES else 0)

            st.subheader("連結與備註")
            source_url = st.text_input("廠商素材來源網址", value=row.get("source_url",""))
            output_url = st.text_input("成品網址", value=row.get("output_url",""))
            labor_year = st.text_input("勞保申報年份", value=row.get("labor_year",""))
            notes      = st.text_area("備註", value=row.get("notes",""))

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
            update_case(row["case_id"], updates)
            st.success("✅ 已儲存！")
            st.rerun()

        if del_btn:
            delete_case(row["case_id"])
            st.success("🗑️ 案件已刪除。")
            st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# 📤 匯出報表
# ════════════════════════════════════════════════════════════════════════════
elif page == "📤 匯出報表":
    st.title("📤 匯出報表")
    if not rows:
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

        filtered = rows
        if exp_vendor:   filtered = [r for r in filtered if exp_vendor in r.get("vendor","")]
        if exp_assignee: filtered = [r for r in filtered if exp_assignee in r.get("assignee","")]
        if exp_status:   filtered = [r for r in filtered if r.get("case_status") in exp_status]
        if start_filter: filtered = [r for r in filtered if r.get("start_date","") >= start_filter]
        if end_filter:   filtered = [r for r in filtered if r.get("start_date","") <= end_filter]
        if exp_year:     filtered = [r for r in filtered if r.get("labor_year","") == exp_year]

        st.markdown(f"篩選結果：**{len(filtered)}** 筆")
        if filtered:
            total_num = sum(float(r.get("total_amount") or 0) for r in filtered)
            st.metric("篩選結果總金額", f"${total_num:,.0f}")

        export_df = pd.DataFrame(filtered)[[
            "vendor","contact_person","assignee","project_name","project_type",
            "case_status","start_date","deadline",
            "deposit_amount","deposit_status","final_amount","final_status","total_amount",
            "source_url","output_url","labor_year","notes","created_at","updated_at"
        ]] if filtered else pd.DataFrame()

        if not export_df.empty:
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

    tc1, tc2 = st.columns(2)
    t_deposit = tc1.number_input("前金金額", min_value=0, value=0, step=100)
    t_final   = tc2.number_input("後金金額", min_value=0, value=0, step=100)
    t_total   = t_deposit + t_final

    r1, r2, r3 = st.columns(3)
    r1.metric("前金",   f"${t_deposit:,}")
    r2.metric("後金",   f"${t_final:,}")
    r3.metric("總金額", f"${t_total:,}")

    st.markdown("---")
    st.subheader("扣除費用試算")

    fc = st.columns(3)
    fee1_name = fc[0].text_input("費用項目 1", value="平台手續費")
    fee1_rate = fc[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.5, key="f1r")
    fee1_amt  = t_total * fee1_rate / 100
    fc[2].metric(fee1_name, f"-${fee1_amt:,.0f}")

    fc2 = st.columns(3)
    fee2_name = fc2[0].text_input("費用項目 2", value="所得稅預扣")
    fee2_rate = fc2[1].number_input("百分比 (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="f2r")
    fee2_amt  = t_total * fee2_rate / 100
    fc2[2].metric(fee2_name, f"-${fee2_amt:,.0f}")

    st.markdown(f"### 實拿金額：**${t_total - fee1_amt - fee2_amt:,.0f}**")

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
