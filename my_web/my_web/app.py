import streamlit as st
import pandas as pd
import datetime
import sqlite3
import plotly.express as px
from streamlit_calendar import calendar
import json  # 用于处理 tags 的存储

# ==========================================
# 1. 数据库管理 (Database Manager)
# ==========================================
DB_FILE = 'my_notion.db'


def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 题目表 (tags 字段改为 TEXT，存储 JSON 字符串)
    c.execute('''CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        difficulty TEXT,
        tags TEXT, -- 存储 JSON 字符串，例如 '["数组", "哈希表"]'
        link TEXT,
        description TEXT,
        solution_code TEXT,
        notes TEXT,
        created_at DATE
    )''')

    # 刷题日志表 (用于日历显示)
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER,
        log_date DATE,
        status TEXT,
        FOREIGN KEY(problem_id) REFERENCES problems(id)
    )''')

    # 资源表
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        url TEXT,
        image_url TEXT,
        status TEXT
    )''')

    # 笔记本表
    c.execute('''CREATE TABLE IF NOT EXISTS notebooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at DATE
    )''')

    # 笔记表 (属于某个笔记本)
    c.execute('''CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        notebook_id INTEGER,
        title TEXT NOT NULL,
        content TEXT,
        created_at DATE,
        updated_at DATE,
        FOREIGN KEY(notebook_id) REFERENCES notebooks(id)
    )''')

    conn.commit()
    conn.close()


def run_query(query, params=(), fetch=False, get_lastrowid=False):
    """
    执行SQL通用函数。
    - fetch=True: 返回查询结果 (list of dict)。
    - get_lastrowid=True: 如果是 INSERT 语句，返回新插入行的 ID。
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问
    c = conn.cursor()
    c.execute(query, params)

    if fetch:
        data = c.fetchall()
        conn.close()
        return [dict(row) for row in data]
    else:  # For INSERT, UPDATE, DELETE
        last_id = None
        if get_lastrowid:
            last_id = c.lastrowid
        conn.commit()
        conn.close()
        return last_id if get_lastrowid else None


# 初始化数据库 (如果是第一次运行)
init_db()

# ==========================================
# 2. 页面配置与样式
# ==========================================
st.set_page_config(
    page_title="Lyn的个人空间",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义 CSS：美化界面
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans SC', sans-serif; }
    h1, h2, h3 { color: #37352f; font-weight: 700; }
    .stMetric { background-color: #f7f6f3; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px; }

    /* 解决顶部白色条挡住按钮的问题：增加顶部内边距 */
    /* Streamlit 的主要内容容器通常有一个 .block-container 类 */
    .block-container { 
        padding-top: 3rem; /* 调整这个值以适配实际遮挡情况 */
    }

    /* 模拟 Notion 标签 */
    .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; margin-bottom: 5px; }
    .tag-easy { background: #e6fcf5; color: #0ca678; } /* 简单 */
    .tag-medium { background: #fff3bf; color: #f59f00; } /* 中等 */
    .tag-hard { background: #fff5f5; color: #fa5252; } /* 困难 */
    .tag-custom { background: #e8f5ff; color: #1971c2; } /* 自定义标签 */

    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #f7f6f3; /* Notion 风格的浅色背景 */
    }

    /* 移除所有针对st.button内部HTML内容的样式，因为不再直接传入HTML */
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心逻辑与页面路由
# ==========================================

# 获取当前 URL 参数，用于页面跳转
query_params = st.query_params


def navigate_to(page_name, **kwargs):
    """辅助函数：更新 URL 参数以实现跳转"""
    # 确保清空所有旧参数，只设置新参数
    st.query_params.clear()
    st.query_params["page"] = page_name
    for key, value in kwargs.items():
        st.query_params[key] = value
    st.rerun()


def go_back(target_page_default="code_problems"):
    """返回上一页"""
    # 智能判断返回页面
    if st.session_state.get('prev_page_on_detail') == 'calendar':
        navigate_to("calendar")
    else:
        navigate_to(target_page_default)


# ==========================================
# 4. 侧边栏导航
# ==========================================
st.sidebar.title("工作台")

# 检查当前页是否是详情页，如果是则不显示主导航
current_page_param = query_params.get("page", "dashboard")

if current_page_param not in ["problem_detail", "notebook_detail"]:
    page_selection = st.sidebar.radio(
        "导航",
        ["🏠 仪表盘", "💻 刷题本", "📅 日历行程", "📦 资源库", "📓 笔记本"],
        # 根据当前 query_params 调整初始选中项
        index=["dashboard", "code_problems", "calendar", "resources", "notebook"].index(
            current_page_param) if current_page_param in ["dashboard", "code_problems", "calendar", "resources",
                                                          "notebook"] else 0
    )
    # 映射中文选项到内部英文 ID
    page_map = {
        "🏠 仪表盘": "dashboard",
        "💻 刷题本": "code_problems",
        "📅 日历行程": "calendar",
        "📦 资源库": "resources",
        "📓 笔记本": "notebook"
    }
    current_page = page_map[page_selection]
else:
    current_page = current_page_param  # 保持在详情页或笔记本详情页

st.sidebar.markdown("---")

# --- 笔记本目录 (仅当在笔记本详情页时显示) ---
if current_page == "notebook_detail":
    notebook_id = query_params.get("notebook_id")
    if notebook_id:
        st.sidebar.subheader("📓 笔记目录")
        notes_in_notebook = run_query("SELECT id, title FROM notes WHERE notebook_id=? ORDER BY created_at DESC",
                                      (notebook_id,), fetch=True)

        # 新建笔记按钮
        if st.sidebar.button("➕ 新建笔记"):
            new_note_id = run_query(
                "INSERT INTO notes (notebook_id, title, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (notebook_id, "无标题笔记", "", datetime.date.today(), datetime.date.today()),
                get_lastrowid=True)  # 获取新插入的ID
            st.toast("已创建新笔记！")
            navigate_to("notebook_detail", notebook_id=notebook_id, note_id=new_note_id)  # 跳转到新笔记

        # 列出所有笔记
        for note in notes_in_notebook:
            button_label = note['title']
            # 用前缀表示选中状态，因为无法直接修改按钮样式
            if query_params.get("note_id") == str(note['id']):
                button_label = f"▸ {note['title']}"

            if st.sidebar.button(button_label, key=f"note_sidebar_{note['id']}"):
                navigate_to("notebook_detail", notebook_id=notebook_id, note_id=note['id'])

        st.sidebar.markdown("---")
        if st.sidebar.button("⬅️ 返回笔记本列表"):
            navigate_to("notebook")

# ==========================================
# 5. 页面内容实现
# ==========================================

# --- 🏠 仪表盘 ---
if current_page == "dashboard":
    st.title("🏠 下午好，Lyn")
    st.caption("这里是你的概览。")

    # 统计数据
    problem_count = run_query("SELECT COUNT(*) as c FROM logs WHERE status='已完成'", fetch=True)[0]['c']
    resource_count = run_query("SELECT COUNT(*) as c FROM resources", fetch=True)[0]['c']
    notebook_count = run_query("SELECT COUNT(*) as c FROM notebooks", fetch=True)[0]['c']

    col_dash1, col_dash2, col_dash3 = st.columns(3)
    col_dash1.metric("已解决题目", str(problem_count))
    col_dash2.metric("资源收藏", str(resource_count))
    col_dash3.metric("笔记本数量", str(notebook_count))

    st.divider()

    # 近期活动 (示例，可根据日志表数据丰富)
    st.subheader("📢 近期动态")
    latest_logs = run_query("""
        SELECT logs.log_date, problems.title FROM logs JOIN problems ON logs.problem_id = problems.id
        ORDER BY logs.log_date DESC LIMIT 5
    """, fetch=True)
    if latest_logs:
        for log in latest_logs:
            st.markdown(f"**{log['log_date']}**: 完成了题目 **[{log['title']}]**")
    else:
        st.info("暂无近期活动。")

# --- 💻 刷题本 (包含列表和详情页逻辑) ---
elif current_page == "code_problems":
    st.title("💻 算法题库")

    # 筛选器
    col_filter1, col_filter2 = st.columns([1, 2])
    all_difficulties = ["所有", "简单", "中等", "困难"]
    selected_difficulty = col_filter1.selectbox("按难度筛选", all_difficulties, key="diff_filter")

    # 获取所有 unique tags
    all_problems_for_tags = run_query("SELECT tags FROM problems WHERE tags IS NOT NULL", fetch=True)
    unique_tags = set()
    for item in all_problems_for_tags:
        try:
            tags_list = json.loads(item['tags'])
            for tag in tags_list:
                unique_tags.add(tag)
        except (json.JSONDecodeError, TypeError):
            pass  # 忽略无效的 JSON

    available_tags = sorted(list(unique_tags))
    selected_tags = col_filter2.multiselect("按标签筛选", available_tags, key="tags_filter")

    # 顶部添加按钮
    with st.expander("➕ 添加新题目"):
        with st.form("new_problem"):
            c1, c2 = st.columns([3, 1])
            new_title = c1.text_input("题目名称", key="add_title")
            new_diff = c2.selectbox("难度", ["简单", "中等", "困难"], key="add_diff")

            # 标签输入
            new_tags_input = st.text_input("标签 (用逗号分隔，如: 数组,哈希表)", key="add_tags")

            new_desc = st.text_area("题目描述简要", key="add_desc")
            submitted = st.form_submit_button("保存题目")
            if submitted and new_title:
                tags_list = [t.strip() for t in new_tags_input.split(',') if t.strip()]
                tags_json = json.dumps(tags_list, ensure_ascii=False)  # 确保中文标签正常存储
                run_query(
                    "INSERT INTO problems (title, difficulty, tags, description, created_at) VALUES (?, ?, ?, ?, ?)",
                    (new_title, new_diff, tags_json, new_desc, datetime.date.today()))
                st.success("题目已添加！")
                st.rerun()

    # 读取题目列表 (应用难度筛选)
    query = "SELECT * FROM problems WHERE 1=1"
    params = []

    if selected_difficulty != "所有":
        query += " AND difficulty = ?"
        params.append(selected_difficulty)

    query += " ORDER BY id DESC"
    all_filtered_by_difficulty_problems = run_query(query, params, fetch=True)

    # 在Python中进行标签筛选
    problems_to_display = []
    if selected_tags:
        for p in all_filtered_by_difficulty_problems:
            try:
                p_tags = json.loads(p['tags']) if p['tags'] else []
                # 检查题目的任何标签是否在 selected_tags 中
                if any(tag in selected_tags for tag in p_tags):
                    problems_to_display.append(p)
            except (json.JSONDecodeError, TypeError):
                # 如果 tags 解析失败，默认不显示（或者根据需求决定是否显示）
                pass
    else:
        problems_to_display = all_filtered_by_difficulty_problems

    if not problems_to_display:
        st.info("没有找到符合条件的题目。")
    else:
        # 自定义表格显示
        for p in problems_to_display:
            # 难度颜色处理
            color = "#0ca678" if p['difficulty'] == "简单" else ("#f59f00" if p['difficulty'] == "中等" else "#fa5252")

            # 卡片布局
            # MODIFICATION 1: 调整 col_action 宽度以容纳更多按钮并使其更窄
            col_mark, col_info, col_action = st.columns([0.2, 8, 1.8])  # Adjusted width for col_action
            with col_mark:
                st.markdown(
                    f"<div style='margin-top:10px; width:10px; height:40px; background:{color}; border-radius:4px;'></div>",
                    unsafe_allow_html=True)
            with col_info:
                st.markdown(f"**{p['title']}**", unsafe_allow_html=True)
                st.caption(f"难度: {p['difficulty']} | 创建日期: {p['created_at']}")
                # 显示标签
                try:
                    p_tags = json.loads(p['tags']) if p['tags'] else []
                    tags_html = "".join([f"<span class='tag tag-custom'>{tag}</span>" for tag in p_tags])
                    if tags_html:
                        st.markdown(tags_html, unsafe_allow_html=True)
                except (json.JSONDecodeError, TypeError):
                    pass
            with col_action:
                # 查看详情（现在详情页也支持编辑）
                if st.button("查看详情", key=f"btn_view_{p['id']}", use_container_width=True):
                    navigate_to("problem_detail", id=p['id'], source="code_problems")

                # 删除按钮及确认逻辑
                # 使用 session_state 来存储当前正在等待确认删除的题目ID
                if 'confirm_delete_problem_id' not in st.session_state:
                    st.session_state['confirm_delete_problem_id'] = None

                if st.session_state['confirm_delete_problem_id'] == p['id']:
                    st.warning(f"确定删除 '{p['title']}' 吗？此操作会同时删除所有相关打卡日志且无法撤销！")
                    col_confirm_del1, col_confirm_del2 = st.columns(2)
                    with col_confirm_del1:
                        if st.button("✅ 确认删除", key=f"confirm_del_{p['id']}", use_container_width=True):
                            # 先删除 logs 中的相关记录
                            run_query("DELETE FROM logs WHERE problem_id=?", (p['id'],))
                            # 再删除 problems 中的题目
                            run_query("DELETE FROM problems WHERE id=?", (p['id'],))
                            st.success(f"题目 '{p['title']}' 及相关日志已删除。")
                            st.session_state['confirm_delete_problem_id'] = None  # 清除确认状态
                            st.rerun()
                    with col_confirm_del2:
                        if st.button("❌ 取消", key=f"cancel_del_{p['id']}", use_container_width=True):
                            st.session_state['confirm_delete_problem_id'] = None  # 清除确认状态
                            st.rerun()
                else:
                    if st.button("🗑️ 删除", key=f"btn_del_{p['id']}", type="secondary", use_container_width=True):
                        st.session_state['confirm_delete_problem_id'] = p['id']  # 设置当前题目为待确认删除状态
                        st.rerun()
            st.divider()

# --- 📝 题目详情页 (独立页面) ---
elif current_page == "problem_detail":
    p_id = query_params.get("id")
    source_page = query_params.get("source", "code_problems")  # 记录是从哪来的(日历还是列表)

    # 将来源页面保存到 session_state，以便 go_back 函数使用
    if 'prev_page_on_detail' not in st.session_state:
        st.session_state['prev_page_on_detail'] = source_page
    else:  # 如果在详情页内部切换了，更新来源
        if query_params.get("source"):
            st.session_state['prev_page_on_detail'] = query_params.get("source")

    if p_id:
        p_data = run_query("SELECT * FROM problems WHERE id=?", (p_id,), fetch=True)
        if p_data:
            problem = p_data[0]

            # 顶部返回按钮 (删除顶上的删除按钮，并让返回按钮占据完整宽度)
            col_back_btn = st.columns([1])[0]  # 调整为单列
            with col_back_btn:
                if st.button("⬅️ 返回"):
                    go_back()

            # --- 题目名称、难度、标签排列在一行 (只读显示) ---
            # 准备标签的HTML
            problem_tags_html = ""
            try:
                p_tags_list = json.loads(problem['tags']) if problem['tags'] else []
                problem_tags_html = "".join(
                    [f"<span class='tag tag-custom' style='margin-right: 5px; margin-bottom: 0;'>{tag}</span>" for tag
                     in p_tags_list])
            except (json.JSONDecodeError, TypeError):
                pass

            # 难度颜色
            difficulty_bg_color = '#e6fcf5' if problem['difficulty'] == '简单' else (
                '#fff3bf' if problem['difficulty'] == '中等' else '#fff5f5')
            difficulty_text_color = '#0ca678' if problem['difficulty'] == '简单' else (
                '#f59f00' if problem['difficulty'] == '中等' else '#fa5252')

            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 5px; margin-top: 15px;">
                    <h1 style="margin: 0; font-size: 2em;">{problem['title']}</h1>
                    <span style="
                        display: inline-block;
                        padding: 4px 10px;
                        border-radius: 6px;
                        font-weight: bold;
                        font-size: 0.9em;
                        background-color: {difficulty_bg_color};
                        color: {difficulty_text_color};
                    ">{problem['difficulty']}</span>
                    <div style="display: flex; flex-wrap: wrap; align-items: center;">
                        {problem_tags_html}
                    </div>
                </div>
            """, unsafe_allow_html=True)

            st.markdown(f"📅 创建于 {problem['created_at']}")  # 保持创建日期显示

            # --- 编辑区域 ---
            # Removed st.subheader("📝 编辑题目信息") and the markdown labels for inputs

            # Then, display the input widgets themselves in a row, using hidden labels
            col_edit_title, col_edit_diff, col_edit_tags = st.columns([3, 1, 2])

            with col_edit_title:
                edited_title = st.text_input("题目名称", value=problem['title'],
                                             key="edit_title")  # label_visibility="hidden" removed to make the label visible by default

            with col_edit_diff:
                all_difficulties = ["简单", "中等", "困难"]
                # 找到当前难度的索引，如果找不到默认为0
                initial_difficulty_index = all_difficulties.index(problem['difficulty']) if problem[
                                                                                                'difficulty'] in all_difficulties else 0
                edited_difficulty = st.selectbox("难度", all_difficulties, index=initial_difficulty_index,
                                                 key="edit_difficulty")  # label_visibility="hidden" removed

            with col_edit_tags:
                # 将 JSON 字符串转换为逗号分隔的字符串以便编辑
                current_tags_str = ""
                try:
                    p_tags = json.loads(problem['tags']) if problem['tags'] else []
                    current_tags_str = ", ".join(p_tags)
                except (json.JSONDecodeError, TypeError):
                    # 忽略无效 JSON，将其视为空字符串
                    pass
                edited_tags_input = st.text_input("标签 (用逗号分隔，如: 数组,哈希表)", value=current_tags_str,
                                                  key="edit_tags_input")  # label_visibility="hidden" removed

            # 主要内容区 (描述、笔记、代码)
            c1, c2 = st.columns([1, 1])

            with c1:
                st.subheader("📄 题目描述")
                desc = st.text_area("描述", value=problem['description'] or "", height=200, key="desc_input")

                st.subheader("💡 思考与笔记")
                notes = st.text_area("在这里写下你的思路...", value=problem['notes'] or "", height=300,
                                     key="notes_input")

            with c2:
                st.subheader("💻 代码解答")
                code = st.text_area("Python 代码",
                                    value=problem['solution_code'] or "class Solution:\n    def solve(self):",
                                    height=560, key="code_input")

            # 底部保存按钮
            if st.button("💾 保存所有修改", type="primary"):
                # 将编辑后的标签字符串转换回 JSON 格式
                edited_tags_list = [t.strip() for t in edited_tags_input.split(',') if t.strip()]
                edited_tags_json = json.dumps(edited_tags_list, ensure_ascii=False)  # 确保中文标签正常存储

                run_query("""
                    UPDATE problems SET title=?, difficulty=?, tags=?, description=?, notes=?, solution_code=? WHERE id=?
                """, (edited_title, edited_difficulty, edited_tags_json, desc, notes, code, p_id))
                st.toast("✅ 保存成功！")
                st.rerun()  # 重新加载页面以即时显示更改

            st.divider()

            # 打卡区 (关联日历)
            st.subheader("📅 提交记录 (同步至日历)")
            col_log1, col_log2 = st.columns([2, 1])
            with col_log1:
                log_date = st.date_input("打卡日期", datetime.date.today())
            with col_log2:
                if st.button("✅ 今日已刷 (打卡)"):
                    run_query("INSERT INTO logs (problem_id, log_date, status) VALUES (?, ?, ?)",
                              (p_id, log_date, "已完成"))
                    st.success("已打卡！请去日历查看。")

# --- 📅 日历行程 ---
elif current_page == "calendar":
    st.title("📅 学习日历")

    # 获取打卡记录
    logs = run_query("""
        SELECT logs.id, logs.log_date, problems.title, problems.id as pid, problems.difficulty
        FROM logs
        JOIN problems ON logs.problem_id = problems.id
        ORDER BY logs.log_date DESC
    """, fetch=True)

    events = []
    for log in logs:
        color = "#0ca678" if log['difficulty'] == "简单" else ("#f59f00" if log['difficulty'] == "中等" else "#fa5252")
        events.append({
            "title": f"{log['title']}",
            "start": log['log_date'],
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {"pid": log['pid']}  # 传递自定义数据
        })

    calendar_options = {
        "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth"},
        "initialView": "dayGridMonth",
        "editable": False,  # 不允许拖拽修改
    }

    # 渲染日历
    # `key`很重要，避免 Streamlit 重用组件状态
    cal_output = calendar(events=events, options=calendar_options, key="my_calendar", custom_css="""
        .fc-event { cursor: pointer; }
    """)

    # 处理日历点击跳转
    if cal_output.get("eventClick"):
        event_data = cal_output["eventClick"]["event"]
        clicked_pid = event_data["extendedProps"]["pid"]
        # 记录是从日历进入的，以便返回时能正确跳转
        st.session_state['prev_page_on_detail'] = 'calendar'
        navigate_to("problem_detail", id=clicked_pid, source="calendar")

# --- 📦 资源库 ---
elif current_page == "resources":
    st.title("📦 资源收藏夹")

    with st.expander("➕ 添加新资源", expanded=False):
        with st.form("add_res"):
            r_title = st.text_input("资源名称", key="res_title")
            r_cat = st.selectbox("分类", ["书籍", "文章", "视频", "工具", "网站"], key="res_cat")
            r_url = st.text_input("链接 URL", key="res_url")
            r_img = st.text_input("封面图片 URL (可选)", placeholder="https://...", key="res_img")
            sub_res = st.form_submit_button("添加")
            if sub_res and r_title:
                run_query("INSERT INTO resources (title, category, url, image_url, status) VALUES (?, ?, ?, ?, ?)",
                          (r_title, r_cat, r_url, r_img, "待看"))
                st.success("资源已添加！")
                st.rerun()

    # 获取所有资源
    resources = run_query("SELECT * FROM resources ORDER BY id DESC", fetch=True)

    if not resources:
        st.info("还没有资源，快去添加一个吧！")
    else:
        # 简单的网格布局
        cols = st.columns(3)
        for idx, res in enumerate(resources):
            with cols[idx % 3]:
                with st.container(border=True):
                    if res['image_url']:
                        st.image(res['image_url'], use_container_width=True, caption=res['title'])
                    else:
                        st.markdown(f"**{res['title']}**")  # 占位符
                    st.caption(f"🏷️ {res['category']}")
                    if res['url']:
                        # 同时显示文本链接和可点击链接
                        st.markdown(f"链接: <a href='{res['url']}' target='_blank'>{res['url']}</a>",
                                    unsafe_allow_html=True)

                    delete_col, _ = st.columns([0.5, 0.5])
                    with delete_col:
                        if st.button("🗑️ 删除", key=f"del_res_{res['id']}"):
                            run_query("DELETE FROM resources WHERE id=?", (res['id'],))
                            st.rerun()

# --- 📓 笔记本列表 ---
elif current_page == "notebook":
    st.title("📓 我的笔记本")

    with st.expander("➕ 新建笔记本", expanded=False):
        # Initialize session state for input if not present
        if 'nb_name_input_value' not in st.session_state:
            st.session_state.nb_name_input_value = ""

        with st.form("new_notebook_form"):
            nb_name = st.text_input("笔记本名称", value=st.session_state.nb_name_input_value, key="nb_name_form_input")
            submitted = st.form_submit_button("创建笔记本")
            if submitted:
                if nb_name:
                    try:
                        run_query("INSERT INTO notebooks (name, created_at) VALUES (?, ?)",
                                  (nb_name, datetime.date.today()))
                        st.success(f"笔记本 '{nb_name}' 已创建！")
                        st.session_state.nb_name_input_value = ""  # Clear the input field in session state
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"笔记本名称 '{nb_name}' 已存在，请更换一个。")
                else:
                    st.error("笔记本名称不能为空。")

    notebooks = run_query("SELECT * FROM notebooks ORDER BY created_at DESC", fetch=True)

    if not notebooks:
        st.info("还没有笔记本，快去创建一个吧！")
    else:
        # 使用 4 等宽列来放置笔记本
        cols_nb = st.columns(4)

        for idx, nb in enumerate(notebooks):
            with cols_nb[idx % 4]:  # 将每个笔记本卡片放置在 4 个内容列中的一个
                # Card content: title and date inside the div
                st.markdown(f"""
                <div style="
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 10px;
                    margin-bottom: 5px; /* Space between card and buttons below */
                    text-align: left;
                    width: 100%;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                    min-height: 100px; /* Adjusted min-height to fit title + date */
                    display: flex;
                    flex-direction: column;
                    justify-content: flex-start;
                ">
                    <h3 style="margin-top: 0; margin-bottom: 5px; color: #37352f; font-size: 1.1em; word-break: break-word;">{nb['name']}</h3>
                    <p style="font-size:0.8em; color:gray; margin-bottom: 0;">创建于 {nb['created_at']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Buttons in a new row of columns, immediately after the card div
                # Adjusted column ratios to give buttons more space for horizontal display
                button_col_enter, spacer_col, button_col_delete, _ = st.columns([2, 0.5, 2, 4.5])

                with button_col_enter:
                    # "进入" button
                    if st.button("进入", key=f"nb_card_click_{nb['id']}", use_container_width=True):
                        navigate_to("notebook_detail", notebook_id=nb['id'])

                with button_col_delete:
                    # "删除" button with trash can icon and secondary type
                    # Only show delete button if not in confirmation state for this notebook
                    if 'confirm_delete_id_notebook' not in st.session_state or st.session_state[
                        'confirm_delete_id_notebook'] != nb['id']:
                        if st.button("删除", key=f"del_nb_{nb['id']}", type="secondary", use_container_width=True):
                            st.session_state['confirm_delete_id_notebook'] = nb['id']
                            st.session_state['confirm_delete_name_notebook'] = nb['name']
                            st.rerun()  # Re-run to display confirmation message

                # If the current notebook is pending deletion, display confirmation message
                if 'confirm_delete_id_notebook' in st.session_state and st.session_state[
                    'confirm_delete_id_notebook'] == nb['id']:
                    st.warning(
                        f"确定要删除笔记本 '{st.session_state['confirm_delete_name_notebook']}' 吗？此操作无法撤销。")
                    # Confirmation buttons use the same column layout as the action buttons
                    confirm_btn_col1, confirm_spacer_col, confirm_btn_col2, _ = st.columns([1, 0.2, 1, 5])
                    with confirm_btn_col1:
                        if st.button("✅ 确认删除", key=f"confirm_del_nb_{nb['id']}"):
                            run_query("DELETE FROM notes WHERE notebook_id=?", (nb['id'],))
                            run_query("DELETE FROM notebooks WHERE id=?", (nb['id'],))
                            st.toast("✅ 笔记本已删除！")
                            # Clear session state for delete confirmation
                            if 'confirm_delete_id_notebook' in st.session_state:
                                del st.session_state['confirm_delete_id_notebook']
                            if 'confirm_delete_name_notebook' in st.session_state:
                                del st.session_state['confirm_delete_name_notebook']
                            st.rerun()
                    with confirm_btn_col2:
                        if st.button("❌ 取消", key=f"cancel_del_nb_{nb['id']}"):
                            # Clear session state for delete confirmation
                            if 'confirm_delete_id_notebook' in st.session_state:
                                del st.session_state['confirm_delete_id_notebook']
                            if 'confirm_delete_name_notebook' in st.session_state:
                                del st.session_state['confirm_delete_name_notebook']
                            st.rerun()


# --- 📝 笔记本详情页 (包含目录和笔记编辑) ---
elif current_page == "notebook_detail":
    notebook_id = query_params.get("notebook_id")
    note_id = query_params.get("note_id")

    if not notebook_id:
        st.error("未指定笔记本ID。")
        navigate_to("notebook")  # 返回笔记本列表
        st.stop()

    notebook_data = run_query("SELECT * FROM notebooks WHERE id=?", (notebook_id,), fetch=True)
    if not notebook_data:
        st.error("找不到该笔记本。")
        navigate_to("notebook")
        st.stop()

    current_notebook = notebook_data[0]
    st.title(f"📓 {current_notebook['name']}")

    # 如果没有指定 note_id，尝试加载最新的一篇笔记，或者提示用户创建
    if not note_id:
        latest_note = run_query("SELECT id FROM notes WHERE notebook_id=? ORDER BY updated_at DESC LIMIT 1",
                                (notebook_id,), fetch=True)
        if latest_note:
            note_id = latest_note[0]['id']
            # 更新URL，让它指向这篇笔记
            navigate_to("notebook_detail", notebook_id=notebook_id, note_id=note_id)
            st.stop()  # 重新运行以加载正确的 note_id
        else:
            st.info("这个笔记本还没有笔记，请在左侧侧边栏点击 '➕ 新建笔记'。")
            st.stop()  # 停止渲染，等待用户创建笔记

    current_note_data = run_query("SELECT * FROM notes WHERE id=? AND notebook_id=?", (note_id, notebook_id),
                                  fetch=True)
    if not current_note_data:
        st.error("找不到这篇笔记。")
        # 尝试跳转到同一个笔记本的最新笔记，如果没有则返回笔记本列表
        latest_note = run_query("SELECT id FROM notes WHERE notebook_id=? ORDER BY updated_at DESC LIMIT 1",
                                (notebook_id,), fetch=True)
        if latest_note:
            navigate_to("notebook_detail", notebook_id=notebook_id, note_id=latest_note[0]['id'])
        else:
            navigate_to("notebook_detail", notebook_id=notebook_id)  # 强制刷新笔记本详情页，会显示“没有笔记”提示
        st.stop()

    current_note = current_note_data[0]

    # 笔记编辑区
    st.subheader(f"📄 {current_note['title']}")

    note_title_edit = st.text_input("笔记标题", value=current_note['title'], key="note_title_edit")
    note_content_edit = st.text_area("笔记内容", value=current_note['content'] or "", height=500,
                                     key="note_content_edit")

    col_note_save, col_note_delete = st.columns([1, 1])
    with col_note_save:
        if st.button("💾 保存笔记", type="primary"):
            run_query("UPDATE notes SET title=?, content=?, updated_at=? WHERE id=?",
                      (note_title_edit, note_content_edit, datetime.date.today(), note_id))
            st.toast("✅ 笔记已保存！")
            st.rerun()  # 重新加载以更新侧边栏目录
    with col_note_delete:
        if st.button("🗑️ 删除笔记", type="secondary"):
            # 为了简化交互，删除操作直接执行，不进行二次确认
            run_query("DELETE FROM notes WHERE id=?", (note_id,))
            st.toast("✅ 笔记已删除！")
            # 删除后回到同一个笔记本的最新笔记，如果没有则返回笔记本列表
            latest_note_after_delete = run_query(
                "SELECT id FROM notes WHERE notebook_id=? ORDER BY updated_at DESC LIMIT 1", (notebook_id,), fetch=True)
            if latest_note_after_delete:
                navigate_to("notebook_detail", notebook_id=notebook_id, note_id=latest_note_after_delete[0]['id'])
            else:
                navigate_to("notebook_detail", notebook_id=notebook_id)  # 强制刷新笔记本详情页，会显示“没有笔记”提示
            st.stop()

    st.markdown(f"<p style='font-size:0.8em; color:gray;'>最后更新于: {current_note['updated_at']}</p>",
                unsafe_allow_html=True)
