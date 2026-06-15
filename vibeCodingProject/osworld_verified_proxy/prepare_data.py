"""生成/准备 OSWorld-Verified 单步代理测试的 demo 数据。

默认生成 8 个合成 GUI 截图 + tasks.json。
如需接入真实 OSWorld 截图，请替换 data/images/ 下的图片并按 tasks.json 格式添加条目。
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

import config


def _get_font(size: int = 20):
    """尝试加载系统字体，失败则使用默认字体。"""
    font_candidates = [
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
        "/System/Library/Fonts/PingFang.ttc",   # macOS 中文
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:/Windows/Fonts/arial.ttf",           # Windows
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _window_chrome(draw: ImageDraw.ImageDraw, width: int, height: int, title: str, font: ImageFont.FreeTypeFont):
    """绘制窗口标题栏和边框。"""
    # 标题栏
    draw.rectangle([0, 0, width, 40], fill="#2d2d2d")
    # 关闭/最小化/最大化按钮
    draw.ellipse([15, 13, 27, 25], fill="#ff5f57")
    draw.ellipse([35, 13, 47, 25], fill="#febc2e")
    draw.ellipse([55, 13, 67, 25], fill="#28c840")
    # 标题文字
    draw.text((width // 2 - len(title) * 6, 10), title, fill="#ffffff", font=font)
    # 窗口背景
    draw.rectangle([0, 40, width, height], fill="#f5f5f5")


def _draw_button(draw: ImageDraw.ImageDraw, bbox, text, font, bg="#4a90d9", fg="#ffffff"):
    """绘制按钮。"""
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle(bbox, radius=6, fill=bg)
    tw, th = draw.textbbox((0, 0), text, font=font)[2:4]
    draw.text(((x1 + x2 - tw) // 2, (y1 + y2 - th) // 2), text, fill=fg, font=font)


def _draw_input(draw: ImageDraw.ImageDraw, bbox, placeholder="", font=None, fg="#333333"):
    """绘制输入框。"""
    x1, y1, x2, y2 = bbox
    draw.rounded_rectangle(bbox, radius=4, fill="#ffffff", outline="#cccccc", width=2)
    if placeholder and font:
        tw, th = draw.textbbox((0, 0), placeholder, font=font)[2:4]
        draw.text((x1 + 10, (y1 + y2 - th) // 2), placeholder, fill="#999999", font=font)


def _draw_icon_label(draw, x, y, color, label, font):
    """绘制带标签的小方块图标。"""
    draw.rectangle([x, y, x + 48, y + 48], fill=color, outline="#cccccc")
    draw.text((x, y + 55), label, fill="#333333", font=font)


def _make_login_form():
    """登录表单截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#e8e8e8")
    draw = ImageDraw.Draw(img)
    font = _get_font(22)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Login", font)

    # 登录面板
    panel_x, panel_y = 312, 180
    panel_w, panel_h = 400, 360
    draw.rounded_rectangle([panel_x, panel_y, panel_x + panel_w, panel_y + panel_h], radius=8, fill="#ffffff", outline="#dddddd")

    draw.text((panel_x + 140, panel_y + 30), "Welcome Back", fill="#333333", font=_get_font(28))

    draw.text((panel_x + 40, panel_y + 90), "Username", fill="#555555", font=small_font)
    _draw_input(draw, [panel_x + 40, panel_y + 115, panel_x + 360, panel_y + 155], "Enter username", small_font)

    draw.text((panel_x + 40, panel_y + 175), "Password", fill="#555555", font=small_font)
    _draw_input(draw, [panel_x + 40, panel_y + 200, panel_x + 360, panel_y + 240], "••••••••", small_font)

    _draw_button(draw, [panel_x + 40, panel_y + 280, panel_x + 360, panel_y + 330], "Sign In", font)

    return img


def _make_file_manager():
    """文件管理器截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#f5f5f5")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Files", font)

    # 侧边栏
    draw.rectangle([0, 40, 220, config.SCREENSHOT_HEIGHT], fill="#ffffff", outline="#e0e0e0")
    items = ["Home", "Desktop", "Documents", "Downloads", "Pictures", "Music"]
    for i, item in enumerate(items):
        y = 70 + i * 45
        color = "#e3f2fd" if item == "Documents" else "#ffffff"
        draw.rectangle([10, y, 210, y + 35], fill=color, outline="#e0e0e0")
        draw.text((25, y + 6), item, fill="#333333", font=small_font)

    # 主区域文件夹
    folders = [("Documents", "#90caf9"), ("Work", "#a5d6a7"), ("Projects", "#ffcc80")]
    for i, (name, color) in enumerate(folders):
        x = 260 + (i % 4) * 180
        y = 100 + (i // 4) * 140
        draw.rectangle([x, y, x + 120, y + 90], fill=color, outline="#bdbdbd")
        draw.text((x + 10, y + 100), name, fill="#333333", font=small_font)

    return img


def _make_settings():
    """设置页截图，含 dark mode 开关。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Settings", font)

    draw.text((60, 80), "Appearance", fill="#333333", font=_get_font(26))
    draw.line([60, 120, 964, 120], fill="#e0e0e0", width=2)

    draw.text((60, 150), "Dark mode", fill="#333333", font=small_font)
    draw.text((60, 175), "Switch to a darker theme", fill="#888888", font=_get_font(14))

    # Toggle switch (off)
    draw.rounded_rectangle([840, 150, 920, 180], radius=15, fill="#cccccc", outline="#bbbbbb")
    draw.ellipse([845, 153, 875, 177], fill="#ffffff")

    return img


def _make_browser():
    """浏览器搜索页截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Browser", font)

    # 地址栏
    draw.rounded_rectangle([120, 55, 904, 90], radius=6, fill="#f1f3f4", outline="#dadce0")
    draw.text((140, 62), "🔍  Search or type a URL", fill="#5f6368", font=small_font)

    # 页面中心 logo + 搜索框
    draw.text((config.SCREENSHOT_WIDTH // 2 - 90, 180), "Search", fill="#4285f4", font=_get_font(48))
    draw.rounded_rectangle([212, 280, 812, 330], radius=24, fill="#ffffff", outline="#dadce0", width=2)
    draw.text((240, 292), "Type your query here", fill="#9aa0a6", font=small_font)

    return img


def _make_spreadsheet():
    """电子表格截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(18)
    small_font = _get_font(14)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Spreadsheet", font)

    # 工具栏
    draw.rectangle([0, 40, config.SCREENSHOT_WIDTH, 90], fill="#f8f9fa", outline="#e0e0e0")
    _draw_button(draw, [20, 50, 100, 80], "Sum", small_font)
    _draw_button(draw, [120, 50, 220, 80], "Chart", small_font)

    # 表格网格
    cols = ["A", "B", "C", "D", "E"]
    rows = ["1", "2", "3", "4", "5"]
    start_x, start_y = 60, 130
    cell_w, cell_h = 120, 40

    for i, col in enumerate(cols):
        draw.rectangle([start_x + i * cell_w, start_y, start_x + (i + 1) * cell_w, start_y + cell_h],
                       fill="#e8f0fe", outline="#dadce0")
        draw.text((start_x + i * cell_w + 50, start_y + 10), col, fill="#333333", font=small_font)

    data = [["10", "20", "30", "40", "50"],
            ["5", "15", "25", "35", "45"],
            ["", "", "", "", ""],
            ["", "", "", "", ""]]
    for r, row in enumerate(rows[1:]):
        for c, col in enumerate(cols):
            x1 = start_x + c * cell_w
            y1 = start_y + (r + 1) * cell_h
            draw.rectangle([x1, y1, x1 + cell_w, y1 + cell_h], fill="#ffffff", outline="#dadce0")
            if data[r][c]:
                draw.text((x1 + 40, y1 + 10), data[r][c], fill="#333333", font=small_font)

    return img


def _make_calendar():
    """日历应用截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Calendar", font)

    draw.text((60, 70), "June 2026", fill="#333333", font=_get_font(30))
    _draw_button(draw, [800, 70, 950, 110], "+ New Event", small_font)

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, day in enumerate(days):
        draw.text((100 + i * 130, 130), day, fill="#666666", font=small_font)

    for week in range(5):
        for day in range(7):
            x = 80 + day * 130
            y = 170 + week * 100
            draw.rectangle([x, y, x + 110, y + 90], fill="#ffffff", outline="#e0e0e0")
            date = week * 7 + day + 1
            if date <= 30:
                draw.text((x + 10, y + 10), str(date), fill="#333333", font=small_font)

    return img


def _make_email():
    """邮件客户端截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Mail", font)

    _draw_button(draw, [40, 60, 180, 100], "✉ Compose", small_font)

    emails = [
        ("Alice", "Meeting tomorrow", "10:30"),
        ("Bob", "Project update", "09:15"),
        ("Carol", "Lunch?", "Yesterday"),
    ]
    for i, (sender, subject, time) in enumerate(emails):
        y = 130 + i * 80
        draw.rectangle([20, y, 1004, y + 75], fill="#f8f9fa" if i % 2 == 0 else "#ffffff", outline="#e0e0e0")
        draw.text((40, y + 10), sender, fill="#333333", font=small_font)
        draw.text((40, y + 38), subject, fill="#666666", font=_get_font(14))
        draw.text((900, y + 25), time, fill="#888888", font=_get_font(14))

    return img


def _make_ide():
    """IDE 截图。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#1e1e1e")
    draw = ImageDraw.Draw(img)
    font = _get_font(18)
    small_font = _get_font(14)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "main.py - IDE", font)

    # 侧边栏文件树
    draw.rectangle([0, 40, 200, config.SCREENSHOT_HEIGHT], fill="#252526", outline="#333333")
    draw.text((20, 60), "EXPLORER", fill="#bbbbbb", font=small_font)
    files = ["main.py", "utils.py", "README.md"]
    for i, f in enumerate(files):
        color = "#ffffff" if f == "main.py" else "#bbbbbb"
        draw.text((30, 90 + i * 28), f, fill=color, font=small_font)

    # 代码区
    code_lines = [
        "def hello_world():",
        "    print('Hello, OSWorld!')",
        "",
        "if __name__ == '__main__':",
        "    hello_world()",
    ]
    for i, line in enumerate(code_lines):
        draw.text((230, 90 + i * 28), line, fill="#d4d4d4", font=small_font)

    # 顶部运行按钮
    _draw_button(draw, [820, 55, 920, 85], "▶ Run", small_font)

    return img


def _make_popup_blocking():
    """弹窗遮挡场景：设置页被登录过期弹窗挡住。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Settings", font)

    # 背景设置项
    draw.text((60, 80), "Appearance", fill="#333333", font=_get_font(26))
    draw.line([60, 120, 964, 120], fill="#e0e0e0", width=2)
    draw.text((60, 150), "Dark mode", fill="#333333", font=small_font)
    draw.text((60, 175), "Switch to a darker theme", fill="#888888", font=_get_font(14))
    # Toggle switch (off)
    draw.rounded_rectangle([840, 150, 920, 180], radius=15, fill="#cccccc", outline="#bbbbbb")
    draw.ellipse([845, 153, 875, 177], fill="#ffffff")

    # 遮挡弹窗
    modal_x, modal_y = 262, 220
    modal_w, modal_h = 500, 220
    draw.rounded_rectangle([modal_x, modal_y, modal_x + modal_w, modal_y + modal_h], radius=10, fill="#ffffff", outline="#cccccc", width=2)
    draw.text((modal_x + 160, modal_y + 40), "Session Expired", fill="#333333", font=_get_font(24))
    draw.text((modal_x + 80, modal_y + 90), "Please log in again to continue.", fill="#666666", font=small_font)
    _draw_button(draw, [modal_x + 180, modal_y + 140, modal_x + 320, modal_y + 185], "OK", small_font)
    # 关闭按钮 X
    draw.text((modal_x + 460, modal_y + 15), "✕", fill="#888888", font=_get_font(20))

    return img


def _make_error_message():
    """错误提示场景：登录页显示密码错误。"""
    img = _make_login_form()
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    # 错误提示条
    draw.rounded_rectangle([312, 150, 712, 195], radius=6, fill="#ffebee", outline="#ef9a9a", width=2)
    draw.text((330, 162), "⚠ Error: Invalid credentials. Please try again.", fill="#c62828", font=small_font)

    # 把 password 输入框标红
    draw.rounded_rectangle([352, 395, 712, 435], radius=4, fill="#ffffff", outline="#ef5350", width=3)

    return img


def _make_scroll_needed():
    """需要滚动的场景：Dark mode 选项完全在页面下方，当前不可见。"""
    img = Image.new("RGB", (config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    _window_chrome(draw, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT, "Settings", font)

    draw.text((60, 80), "Settings", fill="#333333", font=_get_font(30))

    # 填充可视区域的设置项，让 dark mode 完全在下方
    sections = [
        ("Account", ["Username", "Email", "Phone", "Password"]),
        ("Notifications", ["Email alerts", "Push notifications", "SMS", "Marketing"]),
        ("Privacy", ["Profile visible", "Searchable", "Activity status", "Data sharing"]),
        ("Accessibility", ["Font size", "High contrast", "Reduce motion", "Screen reader"]),
    ]
    y = 130
    for title, items in sections:
        draw.text((60, y), title, fill="#333333", font=_get_font(22))
        y += 38
        for item in items:
            draw.text((80, y), item, fill="#555555", font=small_font)
            # toggle
            draw.rounded_rectangle([840, y - 4, 920, y + 24], radius=14, fill="#cccccc")
            y += 42
        y += 12

    # 右下角提示还有更多内容
    draw.rectangle([750, config.SCREENSHOT_HEIGHT - 70, 990, config.SCREENSHOT_HEIGHT - 35],
                   fill="#fff3cd", outline="#ffc107", width=1)
    draw.text((765, config.SCREENSHOT_HEIGHT - 60), "More settings below ▼", fill="#856404", font=small_font)

    # 右侧滚动条：thumb 在上方，暗示下方还有长内容
    draw.rectangle([1004, 40, 1024, 768], fill="#e0e0e0")
    draw.rectangle([1006, 80, 1022, 220], fill="#999999", outline="#888888")

    return img


def _make_notification_banner():
    """底部通知条遮挡场景：浏览器搜索页有 cookie 横幅。"""
    img = _make_browser()
    draw = ImageDraw.Draw(img)
    font = _get_font(20)
    small_font = _get_font(16)

    # 底部 cookie banner
    banner_y = 668
    draw.rectangle([0, banner_y, config.SCREENSHOT_WIDTH, config.SCREENSHOT_HEIGHT], fill="#2c3e50", outline="#1a252f")
    draw.text((40, banner_y + 20), "We use cookies to improve your experience.", fill="#ffffff", font=small_font)
    _draw_button(draw, [740, banner_y + 15, 840, banner_y + 55], "Accept", small_font)
    _draw_button(draw, [860, banner_y + 15, 960, banner_y + 55], "Reject", small_font, bg="#95a5a6")

    return img


TASK_DEFINITIONS = [
    {
        "id": "login_form",
        "instruction": "Log in to the application using username 'user' and password 'pass'.",
        "domain": "login",
        "expected_action": {
            "action": "click",
            "target": "username input field",
            "coords": [360, 295],
        },
    },
    {
        "id": "file_manager",
        "instruction": "Open the Documents folder.",
        "domain": "file_manager",
        "expected_action": {
            "action": "double_click",
            "target": "Documents folder icon",
            "coords": [320, 145],
        },
    },
    {
        "id": "settings_dark_mode",
        "instruction": "Enable dark mode in the settings.",
        "domain": "settings",
        "expected_action": {
            "action": "click",
            "target": "dark mode toggle switch",
            "coords": [880, 165],
        },
    },
    {
        "id": "browser_search",
        "instruction": "Search for 'OSWorld benchmark' using the browser.",
        "domain": "browser",
        "expected_action": {
            "action": "click",
            "target": "search input box",
            "coords": [512, 305],
        },
    },
    {
        "id": "spreadsheet_sum",
        "instruction": "Calculate the sum of values in column A and put the result in cell B1.",
        "domain": "spreadsheet",
        "expected_action": {
            "action": "click",
            "target": "cell B1",
            "coords": [240, 150],
        },
    },
    {
        "id": "calendar_event",
        "instruction": "Create a new calendar event for a meeting at 2 PM tomorrow.",
        "domain": "calendar",
        "expected_action": {
            "action": "click",
            "target": "New Event button",
            "coords": [875, 90],
        },
    },
    {
        "id": "email_compose",
        "instruction": "Compose a new email to support@example.com.",
        "domain": "email",
        "expected_action": {
            "action": "click",
            "target": "Compose button",
            "coords": [110, 80],
        },
    },
    {
        "id": "ide_run",
        "instruction": "Run the Python script currently open in the editor.",
        "domain": "ide",
        "expected_action": {
            "action": "click",
            "target": "Run button",
            "coords": [870, 70],
        },
    },
    {
        "id": "popup_blocking",
        "instruction": "Enable dark mode in the settings.",
        "domain": "settings",
        "expected_action": {
            "action": "click",
            "target": "close button on session expired modal",
            "coords": [720, 235],
        },
    },
    {
        "id": "error_message",
        "instruction": "Log in with username 'user' and password 'pass' after the failed attempt.",
        "domain": "login",
        "expected_action": {
            "action": "click",
            "target": "password input field",
            "coords": [532, 415],
        },
    },
    {
        "id": "scroll_needed",
        "instruction": "Enable dark mode in the settings.",
        "domain": "settings",
        "expected_action": {
            "action": "scroll",
            "target": "settings page",
            "coords": [512, 700],
            "value": "down",
        },
    },
    {
        "id": "notification_banner",
        "instruction": "Search for 'OSWorld benchmark' using the browser.",
        "domain": "browser",
        "expected_action": {
            "action": "click",
            "target": "Accept button on cookie banner",
            "coords": [790, 693],
        },
    },
]

SCREENSHOT_BUILDERS = {
    "login_form": _make_login_form,
    "file_manager": _make_file_manager,
    "settings_dark_mode": _make_settings,
    "browser_search": _make_browser,
    "spreadsheet_sum": _make_spreadsheet,
    "calendar_event": _make_calendar,
    "email_compose": _make_email,
    "ide_run": _make_ide,
    "popup_blocking": _make_popup_blocking,
    "error_message": _make_error_message,
    "scroll_needed": _make_scroll_needed,
    "notification_banner": _make_notification_banner,
}

# 外部真实截图任务（不通过 PIL 生成，需提前放入 data/images/）
EXTERNAL_TASKS = [
    {
        "id": "cnipa_login_captcha",
        "instruction": "Log in as a natural person on this page and complete the slider verification.",
        "domain": "login_captcha",
        "expected_action": {
            "action": "drag",
            "target": "slider puzzle piece",
            "coords": [180, 825, 420, 825],
        },
        "image": "data/images/cnipa_login_captcha.png",
    },
]


def prepare():
    """生成 demo 截图与任务清单。"""
    os.makedirs(config.IMAGES_DIR, exist_ok=True)

    tasks = []
    for task_def in TASK_DEFINITIONS:
        task_id = task_def["id"]
        image_path = os.path.join(config.IMAGES_DIR, f"{task_id}.png")

        builder = SCREENSHOT_BUILDERS[task_id]
        img = builder()
        img.save(image_path)
        print(f"Generated {image_path}")

        # 使用相对路径存储，确保 tasks.json 可移植
        rel_image_path = os.path.relpath(image_path, config.PROJECT_ROOT)
        tasks.append({
            **task_def,
            "image": rel_image_path,
        })

    # 追加外部真实截图任务（如果图片存在）
    for ext_task in EXTERNAL_TASKS:
        image_path = os.path.join(config.PROJECT_ROOT, ext_task["image"])
        if os.path.exists(image_path):
            tasks.append(ext_task)
            print(f"Included external task {ext_task['id']} from {image_path}")
        else:
            print(f"Skipped external task {ext_task['id']}: image not found at {image_path}")

    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    print(f"Wrote {config.TASKS_FILE}")


if __name__ == "__main__":
    prepare()
