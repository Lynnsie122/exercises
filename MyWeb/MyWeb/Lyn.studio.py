import streamlit as st
import pandas as pd
import datetime
import sqlite3
import json
from streamlit_calendar import calendar

# ==========================================
# 1. 数据库逻辑 (保持不变)
# ==========================================
DB_FILE = 'my_notion.db'


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS problems (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, difficulty TEXT, tags TEXT, link TEXT, description TEXT, solution_code TEXT, notes TEXT, created_at DATE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, problem_id INTEGER, log_date DATE, status TEXT)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, url TEXT, image_url TEXT)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS notebooks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created_at DATE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, notebook_id INTEGER, title TEXT, content TEXT, created_at DATE, updated_at DATE)''')
    conn.commit()
    conn.close()


def run_query(query, params=(), fetch=False, get_lastrowid=False):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(query, params)
    if fetch:
        data = c.fetchall()
        conn.close()
        return [dict(row) for row in data]
    else:
        last_id = c.lastrowid if get_lastrowid else None
        conn.commit()
        conn.close()
        return last_id


init_db()

# ==========================================
# 2. UI 样式
# ==========================================
st.set_page_config(page_title="Lyn's Apricot Studio", page_icon="🍊", layout="wide")

# --- 新增：日历专用的 CSS 变量 ---
calendar_style = """
    .fc .fc-button-primary {
        background-color: white !important;
        border: 1.5px solid #FFEDD5 !important;
        color: #5F5A54 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        text-transform: capitalize !important;
    }

    /* 文字居中 */
    .fc-event-title {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        text-align: center !important;
        font-family: 'Quicksand', sans-serif !important;
        font-weight: 700 !important;
    }

    .fc .fc-button-primary:hover {
        border-color: #FFB347 !important;
        color: #FFB347 !important;
        background-color: #FFFBF5 !important;
    }

    /* 修改此处：让激活状态的按钮（如month）也保持白底样式，与today一致 */
    .fc .fc-button-primary.fc-button-active {
        background-color: white !important;
        border-color: #FFEDD5 !important;
        color: #5F5A54 !important;
        box-shadow: none !important;
    }

    /* 激活态按钮的悬停效果 */
    .fc .fc-button-primary.fc-button-active:hover {
        border-color: #FFB347 !important;
        color: #FFB347 !important;
    }

    .fc-event { cursor: pointer !important; }
    .fc-event-title { 
        text-align: center !important; 
        font-weight: 700 !important; 
        font-family: 'Quicksand', sans-serif !important;
    }
"""

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@500;700&family=Noto+Sans+SC:wght@500&display=swap');

    :root {
        --bg-orange: #FFFBF5; 
        --dot-color: #FFD3A3; 
        --card-bg: rgba(255, 255, 255, 0.82);
        --text-main: #5F5A54;
        --mac-orange: #FFEDD5;
        --accent-orange: #FFB347;
    }

    .stApp {
        background-color: var(--bg-orange);
        background-image: radial-gradient(var(--dot-color) 1.8px, transparent 1.8px);
        background-size: 32px 32px;
        background-attachment: fixed;
        color: var(--text-main);
        font-family: 'Quicksand', 'Noto Sans SC', sans-serif;
    }

    .creamy-card {
        background: var(--card-bg);
        backdrop-filter: blur(15px);
        border: 2px solid white;
        border-radius: 32px;
        padding: 24px;
        margin-bottom: 15px;
        box-shadow: 0 8px 25px rgba(255, 179, 71, 0.12);
        transition: all 0.3s ease;
    }
    .creamy-card:hover {
        transform: translateY(-3px);
        border-color: var(--accent-orange);
        box-shadow: 0 12px 30px rgba(255, 179, 71, 0.18);
    }

    /* --- 修改：筛选器卡片样式（让线框更细致贴合） --- */
    [data-testid="stExpander"] {
        background: white !important;
        border: 1px solid #FFEDD5 !important; /* 减细边框，颜色减淡 */
        border-radius: 32px !important;
        box-shadow: 0 4px 15px rgba(255, 179, 71, 0.08) !important;
    }
    [data-testid="stExpander"] > details {
        border: none !important;
    }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(20px);
        border-right: 1px dashed var(--accent-orange);
    }

    .sticker {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 11px;
        font-weight: 700;
        margin-right: 8px;
    }
    .st-orange { background: #FFEDD5; color: #9A3412; }
    .st-green { background: #D1FAE5; color: #065F46; }
    .st-blue { background: #E0F2FE; color: #0369A1; }
    .st-pink { background: #FCE7F3; color: #9D174D; }

    .stButton>button {
        border-radius: 18px !important;
        border: 1.5px solid white !important;
        background: rgba(255,255,255,0.7) !important;
        font-weight: 600 !important;
        color: var(--text-main) !important;
    }
    .stButton>button:hover {
        border-color: var(--accent-orange) !important;
        background: white !important;
        color: var(--accent-orange) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 路由逻辑
# ==========================================
qp = st.query_params


def navigate(page, **kwargs):
    st.query_params.clear()
    st.query_params["page"] = page
    for k, v in kwargs.items(): st.query_params[k] = v
    st.rerun()


with st.sidebar:
    st.markdown("<h3 style='text-align:center; font-family:Quicksand; color:#FFB347;'>Lyn.Studio 🍊</h3>",
                unsafe_allow_html=True)
    curr = qp.get("page", "dashboard")

    nav_options = ["🏠 主页", "💻 题目", "⏳ 日历", "🔗 资源", "📚 笔记"]
    nav_to_page = {"🏠 主页": "dashboard", "💻 题目": "problems", "⏳ 日历": "calendar",
                   "🔗 资源": "resources", "📚 笔记": "notebook"}
    page_to_idx = {v: i for i, v in enumerate(nav_to_page.values())}

    if curr in page_to_idx:
        choice = st.radio("导航", nav_options, index=page_to_idx[curr])
        curr = nav_to_page[choice]
    else:
        st.write("---")
        if st.button("⬅️ 返回主菜单"): navigate("dashboard")

# ==========================================
# 4. 页面内容
# ==========================================

# --- 🏠 主页 ---
if curr == "dashboard":
    st.title("你好，Lyn")
    c1, c2, c3 = st.columns(3)
    p_c = run_query("SELECT COUNT(*) as c FROM problems", fetch=True)[0]['c']
    r_c = run_query("SELECT COUNT(*) as c FROM resources", fetch=True)[0]['c']
    n_c = run_query("SELECT COUNT(*) as c FROM notebooks", fetch=True)[0]['c']

    with c1:
        st.markdown(f"<div class='creamy-card'><h3>{p_c}</h3><p>已收录题目</p></div>", unsafe_allow_html=True)
        if st.button("进入题目列表 💻", use_container_width=True): navigate("problems")
    with c2:
        st.markdown(f"<div class='creamy-card'><h3>{r_c}</h3><p>我的资源</p></div>", unsafe_allow_html=True)
        if st.button("查看我的资源 🔗", use_container_width=True): navigate("resources")
    with c3:
        st.markdown(f"<div class='creamy-card'><h3>{n_c}</h3><p>我的笔记本</p></div>", unsafe_allow_html=True)
        if st.button("打开笔记本 📚", use_container_width=True): navigate("notebook")

# ---💻 题目 ---
elif curr == "problems":
    st.title("题目 💻")
    with st.expander("筛选与新增"):
        f1, f2 = st.columns([1, 2])
        sel_diff = f1.selectbox("难度", ["全部", "简单", "中等", "困难"])
        all_t = run_query("SELECT tags FROM problems", fetch=True)
        unique_t = set()
        for r in all_t:
            for t in json.loads(r['tags'] or "[]"): unique_t.add(t)
        sel_tags = f2.multiselect("标签", list(unique_t))

        st.write("---")
        with st.form("new_p"):
            nt1, nt2, nt3 = st.columns([3, 1, 2])
            n_name = nt1.text_input("题目名称")
            n_diff = nt2.selectbox("难度", ["简单", "中等", "困难"])
            n_tag = nt3.text_input("标签 (用逗号隔开)")
            if st.form_submit_button("新建题目"):
                run_query("INSERT INTO problems (title, difficulty, tags, created_at) VALUES (?,?,?,?)",
                          (n_name, n_diff, json.dumps([x.strip() for x in n_tag.split(',')] if n_tag else []),
                           datetime.date.today()))
                st.rerun()

    problems = run_query("SELECT * FROM problems ORDER BY id DESC", fetch=True)
    if sel_diff != "全部": problems = [x for x in problems if x['difficulty'] == sel_diff]
    if sel_tags: problems = [x for x in problems if any(t in json.loads(x['tags'] or "[]") for t in sel_tags)]

    for p in problems:
        cm, cb = st.columns([8, 1])
        with cm:
            d_style = "st-green" if p['difficulty'] == "简单" else "st-orange" if p['difficulty'] == "中等" else "st-pink"
            tags_html = "".join([f"<span class='sticker st-blue'>{t}</span>" for t in json.loads(p['tags'] or "[]")])
            # 修改：将 div 改为 h3 以对齐笔记本页面的字号
            st.markdown(
                f"<div class='creamy-card' style='margin-bottom:0px;'><span class='sticker {d_style}'>{p['difficulty']}</span> {tags_html}<h3 style='margin-top:10px;'>{p['title']}</h3></div>",
                unsafe_allow_html=True)
        with cb:
            st.write("")
            if st.button("详情", key=f"view_{p['id']}"): navigate("problem_detail", id=p['id'], src="problems")
            if st.session_state.get('conf_p') == p['id']:
                if st.button("✅", key=f"cp_{p['id']}"):
                    run_query("DELETE FROM problems WHERE id=?", (p['id'],))
                    st.session_state.conf_p = None
                    st.rerun()
            else:
                if st.button("删除", key=f"dp_{p['id']}"):
                    st.session_state.conf_p = p['id']
                    st.rerun()
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

# --- 📝 题目详情 (保持不变) ---
elif curr == "problem_detail":
    pid = qp.get("id")
    src = qp.get("src", "problems")
    p = run_query("SELECT * FROM problems WHERE id=?", (pid,), fetch=True)[0]

    back_to = "problems" if src == "problems" else "calendar"
    back_label = "⬅️ 返回列表" if src == "problems" else "⏳ 返回日历"
    if st.button(back_label): navigate(back_to)

    st.title(f"{p['title']}")

    e1, e2, e3 = st.columns([3, 1, 2])
    u_title = e1.text_input("题目名", value=p['title'])
    u_diff = e2.selectbox("难度", ["简单", "中等", "困难"], index=["简单", "中等", "困难"].index(p['difficulty']))
    u_tags = e3.text_input("标签", value=", ".join(json.loads(p['tags'] or "[]")))

    e4, e5 = st.columns(2)
    u_desc = e4.text_area("📄 题目描述", value=p['description'] or "", height=250)
    u_notes = e4.text_area("💡 思路笔记", value=p['notes'] or "", height=250)
    u_code = e5.text_area("💻 代码实现", value=p['solution_code'] or "", height=545)

    st.divider()
    l1, l2 = st.columns([2, 1])
    ld = l1.date_input("记录到日历", datetime.date.today())
    if l2.button("🚀 确认打卡", use_container_width=True):
        run_query("INSERT INTO logs (problem_id, log_date) VALUES (?,?)", (pid, ld))
        st.toast("打卡成功！")

    if st.button("💾 保存同步", type="primary", use_container_width=True):
        run_query(
            "UPDATE problems SET title=?, difficulty=?, tags=?, description=?, notes=?, solution_code=? WHERE id=?",
            (u_title, u_diff, json.dumps([x.strip() for x in u_tags.split(',')] if u_tags else []), u_desc, u_notes,
             u_code, pid))
        st.toast("已同步")
        st.rerun()

# --- ⏳ 日历 ---
elif curr == "calendar":
    st.title("日历 ⏳")
    logs = run_query(
        "SELECT logs.log_date, problems.title, problems.id as pid FROM logs JOIN problems ON logs.problem_id = problems.id",
        fetch=True)
    events = [{"id": str(l['pid']), "title": f"{l['title']}", "start": str(l['log_date']), "backgroundColor": "#FFEDD5",
               "borderColor": "#FFB347", "textColor": "#9A3412"} for l in logs]

    # 修改：将定义的 calendar_style 通过 custom_css 参数注入
    cal_res = calendar(
        events=events,
        options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}},
        custom_css=calendar_style
    )
    if cal_res.get("eventClick"):
        pid = cal_res["eventClick"]["event"]["id"]
        navigate("problem_detail", id=pid, src="calendar")

# --- 🔗 资源 ---
elif curr == "resources":
    st.title("资源 🔗")
    with st.expander("新增资源"):
        with st.form("new_r"):
            rt = st.text_input("名称")
            ru = st.text_input("URL")
            if st.form_submit_button("保存"):
                run_query("INSERT INTO resources (title, url) VALUES (?,?)", (rt, ru))
                st.rerun()

    rs = run_query("SELECT * FROM resources ORDER BY id DESC", fetch=True)
    cols = st.columns(3)
    for i, r in enumerate(rs):
        with cols[i % 3]:
            st.markdown(
                f"<div class='creamy-card'><h4>{r['title']}</h4><p style='font-size:0.8rem; color:#A8A29E; overflow:hidden;'>{r['url']}</p><a href='{r['url']}' target='_blank' style='color:#FFB347;'>立即跳转 ↗</a></div>",
                unsafe_allow_html=True)
            if st.session_state.get('conf_r') == r['id']:
                c1, c2 = st.columns(2)
                if c1.button("✅ 确认", key=f"cr_{r['id']}"):
                    run_query("DELETE FROM resources WHERE id=?", (r['id'],))
                    st.session_state.conf_r = None
                    st.rerun()
                if c2.button("✖️ 取消", key=f"cx_{r['id']}"):
                    st.session_state.conf_r = None
                    st.rerun()
            else:
                if st.button("🗑️ 丢弃", key=f"dr_{r['id']}"):
                    st.session_state.conf_r = r['id']
                    st.rerun()

# --- 📚 笔记 ---
elif curr == "notebook":
    st.title("笔记 📚")
    with st.expander("新建笔记本"):
        nb_name = st.text_input("笔记本标题")
        if st.button("确认创建"):
            run_query("INSERT INTO notebooks (name, created_at) VALUES (?,?)", (nb_name, datetime.date.today()))
            st.rerun()

    nbs = run_query("SELECT * FROM notebooks ORDER BY id DESC", fetch=True)
    for nb in nbs:
        nm, nb_btn = st.columns([8, 1])
        with nm:
            st.markdown(
                f"<div class='creamy-card' style='margin-bottom:0px;'><h3>📓 {nb['name']}</h3><p style='font-size:0.8rem; opacity:0.6;'>创建于 {nb['created_at']}</p></div>",
                unsafe_allow_html=True)
        with nb_btn:
            st.write("")
            if st.button("进入", key=f"enb_{nb['id']}"): navigate("notebook_detail", nid=nb['id'])
            if st.session_state.get('conf_nb') == nb['id']:
                if st.button("✅", key=f"cnb_{nb['id']}"):
                    run_query("DELETE FROM notebooks WHERE id=?", (nb['id'],))
                    st.session_state.conf_nb = None
                    st.rerun()
            else:
                if st.button("删除", key=f"dnb_{nb['id']}"):
                    st.session_state.conf_nb = nb['id']
                    st.rerun()
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

# --- 📒 笔记详情 (保持不变) ---
elif curr == "notebook_detail":
    nid = qp.get("nid")
    active_note = qp.get("active_note")

    with st.sidebar:
        st.subheader("📑 目录")
        notes = run_query("SELECT id, title FROM notes WHERE notebook_id=?", (nid,), fetch=True)
        if st.button("➕ 新增随想", use_container_width=True):
            new_id = run_query("INSERT INTO notes (notebook_id, title, created_at) VALUES (?, '无标题', ?)",
                               (nid, datetime.date.today()), get_lastrowid=True)
            navigate("notebook_detail", nid=nid, active_note=new_id)
        for n in notes:
            if st.button(n['title'], key=f"sn_{n['id']}", use_container_width=True):
                navigate("notebook_detail", nid=nid, active_note=n['id'])
        st.divider()
        if st.button("⬅️ 返回笔记本列表", use_container_width=True): navigate("notebook")

    if active_note:
        note = run_query("SELECT * FROM notes WHERE id=?", (active_note,), fetch=True)[0]
        ut = st.text_input("随想标题", value=note['title'])
        uc = st.text_area("记录此刻的想法...", value=note['content'] or "", height=500)
        if st.button("💾 保存修改", type="primary"):
            run_query("UPDATE notes SET title=?, content=? WHERE id=?", (ut, uc, active_note))
            st.toast("已保存至笔记本")
            st.rerun()
