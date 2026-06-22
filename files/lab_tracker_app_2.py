#!/usr/bin/env python3
"""
实验室工作时长追踪器 - GUI版
- 首次运行弹出设置界面
- 系统托盘图标，后台静默运行
- 自动检测WiFi，记录工作时长
- 支持打包为 .exe
打开本地server
cd "E:\Coin Laundry\LabTracker\files"
python -m http.server 8080
http://localhost:8080/lab_dashboard.html
"""

import subprocess
import json
import time
import threading
import sys
import os
import winreg
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


# ── 路径配置 ──────────────────────────────────
APP_NAME    = "LabTracker"
BASE_DIR    = Path("E:/Coin Laundry/LabTracker/files")
DATA_DIR    = BASE_DIR / "data"
LOG_DIR     = BASE_DIR / "log"
CONFIG_FILE = BASE_DIR / "config.json"
DATA_FILE   = DATA_DIR / "data.json"
LOG_FILE    = LOG_DIR  / "tracker.log"
BASE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── 默认配置 ──────────────────────────────────────
DEFAULT_CONFIG = {
    "target_wifis": [],
    "check_interval": 30,
    "show_settings_on_start": True,
    "autostart": False,
    "last_auto_report_week": None,
}

# ═════════════════════════════════════════════════
# 配置 & 数据 读写
# ═════════════════════════════════════════════════
import random

COMMENTS = {
    "high_total": [
        "这周投入相当可观，注意别把自己榨干了。",
        "高强度的一周，记得犒劳一下自己。",
        "工时拉满，效率看起来很在线。",
        "这周的努力值得被记住。",
    ],
    "low_total": [
        "轻松的一周，状态调整也是工作的一部分。",
        "工时不多，但别给自己太大压力。",
        "这周节奏比较松，也许是在为下一阶段蓄力。",
    ],
    "medium_total": [
        "稳扎稳打的一周，节奏把握得不错。",
        "工作量适中，是个比较舒服的状态。",
        "这周表现平稳，继续保持就很好。",
    ],
    "consistent": [
        "几乎每天都出现在实验室，规律性很强。",
        "持续性不错，习惯正在养成。",
        "稳定输出的一周，节奏感拿捏得很好。",
    ],
    "sporadic": [
        "这周比较集中地爆发了几天，其余时间在休息。",
        "工作日比较少，但每次去都挺投入。",
        "节奏不算规律，但也是一种工作方式。",
    ],
    "long_single_day": [
        "有一天扎进去就出不来了，那种沉浸感很难得。",
        "某天的超长在线，那天大概解决了不少事情。",
        "有一天明显是状态最好的一天。",
    ],
    "morning_person": [
        "看起来上午的状态比较好，是个早起型选手。",
        "上午时段出现得比较多，晨间效率不错。",
    ],
    "afternoon_person": [
        "下午是主战场，午后的专注力看起来不错。",
        "下午时段最活跃，是个午后发力型。",
    ],
    "evening_person": [
        "晚上反而是状态最好的时候，夜猫子型工作者。",
        "夜晚时段出现频率最高，晚上效率似乎更高。",
    ],
    "late_night": [
        "深夜还在线，记得早点休息。",
        "凌晨时段都有记录，作息要注意一下。",
    ],
    "generic": [
        "新的一周，新的状态。",
        "继续保持这个节奏。",
        "每一段记录都是认真投入过的证明。",
    ],
}
def analyze_time_pattern(sessions):
    buckets = {"morning": 0, "afternoon": 0, "evening": 0, "late_night": 0}
    for s in sessions:
        try:
            hour = int(s["start"].split("T")[1].split(":")[0])
        except Exception:
            continue
        if 5 <= hour < 12:
            buckets["morning"] += 1
        elif 12 <= hour < 18:
            buckets["afternoon"] += 1
        elif 18 <= hour < 23:
            buckets["evening"] += 1
        else:
            buckets["late_night"] += 1
    return buckets
def generate_comment(total_hours, work_days, max_day_hours, time_buckets):
    pool = []
    if total_hours > 30:
        pool += COMMENTS["high_total"]
    elif total_hours < 10:
        pool += COMMENTS["low_total"]
    else:
        pool += COMMENTS["medium_total"]
    if work_days >= 5:
        pool += COMMENTS["consistent"]
    elif work_days <= 2:
        pool += COMMENTS["sporadic"]
    if max_day_hours > 6:
        pool += COMMENTS["long_single_day"]
    if time_buckets:
        top = max(time_buckets, key=time_buckets.get)
        if time_buckets[top] > 0:
            key_map = {
                "morning": "morning_person",
                "afternoon": "afternoon_person",
                "evening": "evening_person",
                "late_night": "late_night",
            }
            pool += COMMENTS[key_map[top]]
    return random.choice(pool if pool else COMMENTS["generic"])


def build_weekly_report(data, week_offset=1):
    today = date.today()
    monday = today - timedelta(days=today.weekday() + 7 * week_offset)
    sunday = monday + timedelta(days=6)

    week_sessions = []
    daily_totals = {}
    for i in range(7):
        day = monday + timedelta(days=i)
        key = day.isoformat()
        day_s = [s for s in data["sessions"]
                 if s.get("date") == key and not s.get("_temp")]
        week_sessions.extend(day_s)
        daily_totals[key] = sum(s.get("hours", 0) for s in day_s)

    total_hours = sum(daily_totals.values())
    work_days = sum(1 for h in daily_totals.values() if h > 0)
    max_day_key = max(daily_totals, key=daily_totals.get) if daily_totals else None
    max_day_hours = daily_totals.get(max_day_key, 0) if max_day_key else 0

    time_buckets = analyze_time_pattern(week_sessions)
    bucket_cn = {"morning": "上午", "afternoon": "下午",
                 "evening": "晚上", "late_night": "深夜"}
    fav = max(time_buckets, key=time_buckets.get) if any(time_buckets.values()) else None
    fav_label = bucket_cn.get(fav, "无明显规律")

    comment = generate_comment(total_hours, work_days, max_day_hours, time_buckets)
    weekday_names = ["周一","周二","周三","周四","周五","周六","周日"]

    lines = [
        f"📊 周报：{monday.strftime('%m月%d日')} ~ {sunday.strftime('%m月%d日')}",
        "=" * 36,
    ]
    for i in range(7):
        day = monday + timedelta(days=i)
        key = day.isoformat()
        h = daily_totals.get(key, 0)
        bar = "█" * int(h) + ("▌" if h % 1 >= 0.5 else "")
        marker = "  ← 最长" if key == max_day_key and h > 0 else ""
        lines.append(f"  {weekday_names[i]} {key}  {bar}  {h:.1f}h{marker}")
    lines += [
        "",
        f"总工时：{total_hours:.1f}h",
        f"工作天数：{work_days} 天",
        f"最长单日：{max_day_key}（{max_day_hours:.1f}h）" if max_day_key and max_day_hours > 0 else "",
        f"最爱工作时段：{fav_label}",
        "",
        f"💬 {comment}",
        "=" * 36,
    ]

    return "\n".join(l for l in lines), {
        "week_start": monday.isoformat(),
        "total_hours": round(total_hours, 2),
        "work_days": work_days,
        "comment": comment,
    }
def save_weekly_report_file(report_text, week_start):
    report_file = LOG_DIR / f"weekly_report_{week_start}.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)
    return report_file

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 补全缺失的key
            for k, v in DEFAULT_CONFIG.items():
                cfg.setdefault(k, v)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"sessions": [], "daily": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ═════════════════════════════════════════════════
# WiFi 检测
# ═════════════════════════════════════════════════

def get_current_wifi():
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW  # 加这一行
        )
        raw = result.stdout
        for enc in ("utf-8", "gbk", "cp936", "latin-1"):
            try:
                output = raw.decode(enc)
                break
            except Exception:
                continue
        else:
            return None
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line and ":" in line:
                ssid = line.split(":", 1)[1].strip()
                return ssid if ssid else None
    except Exception as e:
        log(f"WiFi检测出错: {e}")
    return None

def scan_available_wifis():
    """扫描附近可见的WiFi列表"""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks"],
            capture_output=True, timeout=10
        )
        raw = result.stdout
        for enc in ("utf-8", "gbk", "cp936", "latin-1"):
            try:
                output = raw.decode(enc)
                break
            except Exception:
                continue
        else:
            return []
        wifis = []
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("SSID") and "BSSID" not in line and ":" in line:
                ssid = line.split(":", 1)[1].strip()
                if ssid and ssid not in wifis:
                    wifis.append(ssid)
        return wifis
    except Exception:
        return []

# ═════════════════════════════════════════════════
# 开机自启
# ═════════════════════════════════════════════════

def get_exe_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'pythonw "{os.path.abspath(__file__)}"'

def set_autostart(enable: bool):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_exe_path())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log(f"设置开机自启失败: {e}")
        return False

def is_autostart_enabled():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False

# ═════════════════════════════════════════════════
# 记录逻辑
# ═════════════════════════════════════════════════

def date_key(d=None):
    return (d or date.today()).isoformat()

def add_hours(data, day, hours):
    if day not in data["daily"]:
        data["daily"][day] = {"total": 0.0}
    data["daily"][day]["total"] = round(data["daily"][day]["total"] + hours, 2)

# ═════════════════════════════════════════════════
# 设置窗口
# ═════════════════════════════════════════════════

class SettingsWindow:
    def __init__(self, cfg, on_save=None, first_run=False):
        self.cfg = cfg
        self.on_save = on_save
        self.first_run = first_run

        self.root = tk.Tk()
        self.root.title("实验室追踪器 · 设置")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        # 居中显示
        self.root.update_idletasks()
        w, h = 480, 520
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _build_ui(self):
        BG    = "#1a1a2e"
        BG2   = "#16213e"
        CARD  = "#0f3460"
        ACC   = "#e94560"
        TEXT  = "#eaeaea"
        TEXT2 = "#a0a0b0"
        FONT  = ("Segoe UI", 10)
        FONT_B = ("Segoe UI", 10, "bold")
        FONT_H = ("Segoe UI", 14, "bold")

        r = self.root
        r.configure(bg=BG)

        # 标题
        tk.Label(r, text="⚙  追踪器设置", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=TEXT).pack(pady=(20,4))
        if self.first_run:
            tk.Label(r, text="首次使用，请先配置要监控的 WiFi 网络",
                     font=FONT, bg=BG, fg=TEXT2).pack(pady=(0,16))
        else:
            tk.Label(r, text="", bg=BG).pack(pady=4)

        # ── WiFi 列表 ──────────────────────────
        frame_wifi = tk.Frame(r, bg=BG2, bd=0, relief="flat")
        frame_wifi.pack(fill="x", padx=24, pady=4)

        tk.Label(frame_wifi, text="监控的 WiFi 名称", font=FONT_B,
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=14, pady=(12,4))
        tk.Label(frame_wifi, text="连接到这些 WiFi 时自动开始计时",
                 font=("Segoe UI", 9), bg=BG2, fg=TEXT2).pack(anchor="w", padx=14)

        list_frame = tk.Frame(frame_wifi, bg=BG2)
        list_frame.pack(fill="x", padx=14, pady=8)

        self.wifi_listbox = tk.Listbox(list_frame, height=4,
            bg=CARD, fg=TEXT, selectbackground=ACC, selectforeground="#fff",
            font=FONT, bd=0, relief="flat", activestyle="none")
        self.wifi_listbox.pack(side="left", fill="both", expand=True)

        for w in self.cfg.get("target_wifis", []):
            self.wifi_listbox.insert(tk.END, w)

        btn_frame = tk.Frame(list_frame, bg=BG2)
        btn_frame.pack(side="left", padx=(8,0), fill="y")

        tk.Button(btn_frame, text="删除选中", font=("Segoe UI",9),
                  bg="#2d2d44", fg=TEXT, bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._remove_wifi).pack(pady=(0,4))

        # 输入框 + 添加
        input_row = tk.Frame(frame_wifi, bg=BG2)
        input_row.pack(fill="x", padx=14, pady=(0,4))

        self.wifi_entry = tk.Entry(input_row, font=FONT, bg=CARD, fg=TEXT,
                                   insertbackground=TEXT, bd=0, relief="flat")
        self.wifi_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0,8))

        tk.Button(input_row, text="手动添加", font=("Segoe UI",9),
                  bg=ACC, fg="#fff", bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._add_wifi_manual).pack(side="left")

        # 扫描按钮
        scan_row = tk.Frame(frame_wifi, bg=BG2)
        scan_row.pack(fill="x", padx=14, pady=(0,12))

        self.scan_var = tk.StringVar(value="")
        self.scan_combo = ttk.Combobox(scan_row, textvariable=self.scan_var,
                                       font=FONT, state="readonly", width=28)
        self.scan_combo.pack(side="left", fill="x", expand=True, padx=(0,8))

        tk.Button(scan_row, text="🔍 扫描附近WiFi", font=("Segoe UI",9),
                  bg="#2d2d44", fg=TEXT, bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._scan_wifi).pack(side="left", padx=(0,4))

        tk.Button(scan_row, text="添加选中", font=("Segoe UI",9),
                  bg="#2d2d44", fg=TEXT, bd=0, padx=10, pady=4,
                  cursor="hand2", command=self._add_from_scan).pack(side="left")

        # ── 选项 ───────────────────────────────
        frame_opts = tk.Frame(r, bg=BG2)
        frame_opts.pack(fill="x", padx=24, pady=(12,4))

        tk.Label(frame_opts, text="启动选项", font=FONT_B,
                 bg=BG2, fg=TEXT).pack(anchor="w", padx=14, pady=(12,8))

        self.show_settings_var = tk.BooleanVar(value=self.cfg.get("show_settings_on_start", True))
        tk.Checkbutton(frame_opts, text="每次启动时显示设置窗口",
                       variable=self.show_settings_var,
                       font=FONT, bg=BG2, fg=TEXT,
                       selectcolor=CARD, activebackground=BG2,
                       activeforeground=TEXT).pack(anchor="w", padx=14)

        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        tk.Checkbutton(frame_opts, text="开机时自动启动（写入注册表）",
                       variable=self.autostart_var,
                       font=FONT, bg=BG2, fg=TEXT,
                       selectcolor=CARD, activebackground=BG2,
                       activeforeground=TEXT).pack(anchor="w", padx=14, pady=(4,12))

        # ── 保存按钮 ───────────────────────────
        tk.Button(r, text="保存并开始追踪", font=("Segoe UI", 11, "bold"),
                  bg=ACC, fg="#fff", bd=0, padx=24, pady=10,
                  cursor="hand2", command=self._save).pack(pady=20)

    def _remove_wifi(self):
        sel = self.wifi_listbox.curselection()
        if sel:
            self.wifi_listbox.delete(sel[0])

    def _add_wifi_manual(self):
        name = self.wifi_entry.get().strip()
        if name:
            existing = list(self.wifi_listbox.get(0, tk.END))
            if name not in existing:
                self.wifi_listbox.insert(tk.END, name)
            self.wifi_entry.delete(0, tk.END)

    def _scan_wifi(self):
        self.scan_combo.set("扫描中...")
        self.root.update()
        wifis = scan_available_wifis()
        if wifis:
            self.scan_combo["values"] = wifis
            self.scan_combo.set(wifis[0])
        else:
            self.scan_combo["values"] = ["未找到WiFi"]
            self.scan_combo.set("未找到WiFi")

    def _add_from_scan(self):
        name = self.scan_var.get().strip()
        if name and name not in ("扫描中...", "未找到WiFi", ""):
            existing = list(self.wifi_listbox.get(0, tk.END))
            if name not in existing:
                self.wifi_listbox.insert(tk.END, name)

    def _save(self):
        wifis = list(self.wifi_listbox.get(0, tk.END))
        if not wifis:
            messagebox.showwarning("提示", "请至少添加一个 WiFi 名称", parent=self.root)
            return

        self.cfg["target_wifis"] = wifis
        self.cfg["show_settings_on_start"] = self.show_settings_var.get()
        self.cfg["autostart"] = self.autostart_var.get()
        save_config(self.cfg)
        set_autostart(self.autostart_var.get())

        if self.on_save:
            self.on_save(self.cfg)

        self.root.destroy()

    def _on_close(self):
        if self.first_run:
            if messagebox.askyesno("退出", "还未完成设置，确定退出吗？", parent=self.root):
                self.root.destroy()
                sys.exit(0)
        else:
            self.root.destroy()

# ═════════════════════════════════════════════════
# 托盘图标（用tk模拟，不依赖pystray）
# ═════════════════════════════════════════════════

class TrayApp:
    def __init__(self, cfg):
        self.cfg = cfg
        self.data = load_data()
        self._cleanup_temp_on_startup()  # 加这行
        self.session_start = None
        self.in_lab = False
        self.running = True
        self.current_wifi = None

        # 托盘用一个隐藏的tk窗口 + 系统托盘菜单
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_NAME)

        # 右键菜单
        self.menu = tk.Menu(self.root, tearoff=0,
                            bg="#1a1a2e", fg="#eaeaea",
                            activebackground="#e94560",
                            activeforeground="#fff",
                            font=("Segoe UI", 10))
        self.menu.add_command(label="📊 查看状态", command=self._show_status)
        self.menu.add_command(label="📋 生成周报", command=lambda: self._generate_and_show_report(show_popup=True))
        self.menu.add_command(label="⚙  设置",    command=self._open_settings)
        self.menu.add_separator()
        self.menu.add_command(label="❌ 退出",     command=self._quit)

        # 用一个小窗口作为托盘替代（真实托盘需要pystray，这里用最小化窗口）
        self._build_status_bar()

        # 后台追踪线程
        self.track_thread = threading.Thread(target=self._track_loop, daemon=True)
        self.track_thread.start()

        # 每个自然周第一次启动时，自动显示一次上周周报。
        self.root.after(500, self._show_weekly_report_once_per_week)

        self.root.mainloop()

    def _build_status_bar(self):
        """底部状态栏小窗口（替代系统托盘）"""
        self.bar = tk.Toplevel(self.root)
        self.bar.overrideredirect(True)
        self.bar.attributes("-topmost", True)
        self.bar.attributes("-alpha", 0.92)

        sw = self.bar.winfo_screenwidth()
        sh = self.bar.winfo_screenheight()
        w, h = 300, 40
        self.bar.geometry(f"{w}x{h}+{sw-w-12}+{sh-h-52}")

        self.bar.configure(bg="#1a1a2e")

        self.status_dot = tk.Label(self.bar, text="●", font=("Segoe UI", 12),
                                   bg="#1a1a2e", fg="#666")
        self.status_dot.pack(side="left", padx=(10,4))

        self.status_label = tk.Label(self.bar, text="追踪器运行中",
                                     font=("Segoe UI", 10), bg="#1a1a2e", fg="#aaa")
        self.status_label.pack(side="left", fill="x", expand=True)

        self.time_label = tk.Label(self.bar, text="",
                                   font=("Segoe UI", 10, "bold"), bg="#1a1a2e", fg="#eee")
        self.time_label.pack(side="left", padx=(0,8))

        settings_btn = tk.Label(self.bar, text="⚙", font=("Segoe UI", 13),
                                bg="#1a1a2e", fg="#666", cursor="hand2")
        settings_btn.pack(side="right", padx=(0,6))
        settings_btn.bind("<Button-1>", lambda e: self._open_settings())
        # 退出按钮
        quit_btn = tk.Label(self.bar, text="✕", font=("Segoe UI", 11),
                            bg="#1a1a2e", fg="#666", cursor="hand2")
        quit_btn.pack(side="right", padx=(0,2))
        quit_btn.bind("<Button-1>", lambda e: self._quit())
        quit_btn.bind("<Enter>", lambda e: quit_btn.config(fg="#e94560"))
        quit_btn.bind("<Leave>", lambda e: quit_btn.config(fg="#666"))

        # 拖动支持
        self.bar.bind("<Button-1>", self._start_drag)
        self.bar.bind("<B1-Motion>", self._drag)
        self.status_label.bind("<Button-1>", self._start_drag)
        self.status_label.bind("<B1-Motion>", self._drag)
        self.status_dot.bind("<Button-1>", self._start_drag)
        self.status_dot.bind("<B1-Motion>", self._drag)

        # 在状态栏及其主要子控件上右键打开操作菜单。
        for widget in (self.bar, self.status_dot, self.status_label, self.time_label):
            widget.bind("<Button-3>", self._show_menu)

        self._update_ui()

    def _show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _start_drag(self, e):
        self._drag_x = e.x_root - self.bar.winfo_x()
        self._drag_y = e.y_root - self.bar.winfo_y()

    def _drag(self, e):
        self.bar.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _update_ui(self):
        if self.in_lab and self.session_start:
            elapsed = (datetime.now() - self.session_start).total_seconds() / 3600
            h = int(elapsed)
            m = int((elapsed - h) * 60)
            self.status_dot.config(fg="#3fb950")
            self.status_label.config(text=f"记录中 · {self.current_wifi or ''}", fg="#ccc")
            self.time_label.config(text=f"{h}h {m:02d}m")
        else:
            self.status_dot.config(fg="#484f58")
            self.status_label.config(text="等待连接实验室WiFi", fg="#666")
            self.time_label.config(text="")

        if self.running:
            self.bar.after(10000, self._update_ui)

    def _track_loop(self):
        last_flush = datetime.now()
        FLUSH_INTERVAL = 300  # 每5分钟自动写入一次进行中的数据

        while self.running:
            now = datetime.now()
            wifi = get_current_wifi()
            target_wifis = self.cfg.get("target_wifis", [])
            connected = wifi in target_wifis

            if connected and not self.in_lab:
                self.in_lab = True
                self.session_start = now
                self.current_wifi = wifi
                log(f"✅ 检测到 {wifi}，开始记录")

            elif not connected and self.in_lab:
                self.in_lab = False
                if self.session_start:
                    elapsed = (now - self.session_start).total_seconds() / 3600
                    if elapsed > 0.05:
                        day = date_key(self.session_start.date())
                        self._remove_temp_session(day)
                        add_hours(self.data, day, round(elapsed, 2))
                        self.data["sessions"].append({
                            "date": day,
                            "start": self.session_start.isoformat(timespec="minutes"),
                            "end": now.isoformat(timespec="minutes"),
                            "hours": round(elapsed, 2),
                            "wifi": self.current_wifi or "unknown"
                        })
                        save_data(self.data)
                        log(f"⏹  会话结束，记录 {elapsed:.2f}h → {day}")
                    self.session_start = None
                self.current_wifi = None
            # 进行中的会话定期刷入文件（不断开WiFi也能看到实时数据）
            if self.in_lab and self.session_start:
                secs_since_flush = (now - last_flush).total_seconds()
                if secs_since_flush >= FLUSH_INTERVAL:
                    elapsed = (now - self.session_start).total_seconds() / 3600
                    if elapsed > 0.05:
                        day = date_key(self.session_start.date())
                        self._remove_temp_session(day)
                        base_total = (self.data["daily"].get(day) or {"total": 0.0})["total"]
                        tmp_data = {
                            "daily": {
                                **self.data["daily"],
                                day: {"total": round(base_total + elapsed, 2)}
                            },
                            "sessions": self.data["sessions"] + [{
                                "date": day,
                                "start": self.session_start.isoformat(timespec="minutes"),
                                "end": "进行中",
                                "hours": round(elapsed, 2),
                                "wifi": self.current_wifi or "unknown",
                                "_temp": True
                            }]
                        }
                        save_data(tmp_data)
                        last_flush = now
                        log(f"🔄 刷新进行中数据 {elapsed:.2f}h")

            interval = self.cfg.get("check_interval", 30)
            time.sleep(interval)

    def _remove_temp_session(self, day):
        """移除之前刷入的临时进行中会话，避免重复计算"""
        self.data["sessions"] = [
            s for s in self.data["sessions"]
            if not (s.get("_temp") and s.get("date") == day)
        ]
        real_total = sum(
            s["hours"] for s in self.data["sessions"]
            if s.get("date") == day and not s.get("_temp")
        )
        if day in self.data["daily"]:
            self.data["daily"][day]["total"] = round(real_total, 2)
    def _cleanup_temp_on_startup(self):
        """启动时清理临时会话，但把临时工时并入正式记录，不丢数据"""
        temp_sessions = [s for s in self.data["sessions"] if s.get("_temp")]
        for s in temp_sessions:
            day = s.get("date")
            hours = s.get("hours", 0)
            # 把临时工时转为正式记录
            if day:
                if day not in self.data["daily"]:
                    self.data["daily"][day] = {"total": 0.0}
                # daily里已经包含了临时工时，所以只需要把_temp会话改为正式会话
                s.pop("_temp")
                s["end"] = s.get("end", "未知")
        save_data(self.data)

    def _show_status(self):
        today_key = date_key()
        today_h = (self.data["daily"].get(today_key) or {}).get("total", 0)
        cur = ""
        if self.in_lab and self.session_start:
            elapsed = (datetime.now() - self.session_start).total_seconds() / 3600
            cur = f"\n当前会话：{elapsed:.1f}h（进行中）"
        msg = (f"今日已记录：{today_h:.1f}h{cur}\n"
               f"监控 WiFi：{', '.join(self.cfg.get('target_wifis', []))}\n"
               f"数据文件：{DATA_FILE}")
        messagebox.showinfo("追踪状态", msg)

    def _generate_and_show_report(self, show_popup=True):
        """生成并保存上周周报，并按需弹窗显示。"""
        try:
            report_text, summary = build_weekly_report(self.data)
            report_file = save_weekly_report_file(
                report_text, summary["week_start"]
            )
            log(f"已生成上周周报：{report_file}")

            if show_popup:
                def show_report():
                    messagebox.showinfo(
                        "实验室追踪器 · 上周周报",
                        f"{report_text}\n\n已保存到：\n{report_file}",
                    )

                # 周一自动生成发生在后台线程，Tk 弹窗需交回主线程。
                if threading.current_thread() is threading.main_thread():
                    show_report()
                else:
                    self.root.after(0, show_report)

            return report_file
        except Exception as e:
            log(f"生成周报失败：{e}")
            if show_popup:
                def show_error():
                    messagebox.showerror("周报生成失败", str(e))

                if threading.current_thread() is threading.main_thread():
                    show_error()
                else:
                    self.root.after(0, show_error)
            return None

    def _show_weekly_report_once_per_week(self):
        """本周第一次启动时自动弹出上周周报。"""
        iso_year, iso_week, _ = date.today().isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        if self.cfg.get("last_auto_report_week") == week_key:
            return

        report_file = self._generate_and_show_report(show_popup=True)
        if report_file is not None:
            self.cfg["last_auto_report_week"] = week_key
            save_config(self.cfg)

    def _open_settings(self):
        def on_save(new_cfg):
            self.cfg = new_cfg
        SettingsWindow(self.cfg, on_save=on_save, first_run=False)

    def _quit(self):
        # 保存未结束的会话
        if self.in_lab and self.session_start:
            now = datetime.now()
            elapsed = (now - self.session_start).total_seconds() / 3600
            if elapsed > 0.05:
                day = date_key(self.session_start.date())
                add_hours(self.data, day, round(elapsed, 2))
                self.data["sessions"].append({
                    "date": day,
                    "start": self.session_start.isoformat(timespec="minutes"),
                    "end": now.isoformat(timespec="minutes"),
                    "hours": round(elapsed, 2),
                    "wifi": self.current_wifi or "unknown"
                })
                save_data(self.data)
                log(f"退出时保存会话 {elapsed:.2f}h")
        self.running = False
        self.root.destroy()

# ═════════════════════════════════════════════════
# 入口
# ═════════════════════════════════════════════════

def main():
    cfg = load_config()

    # 首次运行 或 设置为每次弹出 → 显示设置窗口
    is_first = not cfg.get("target_wifis")
    if is_first or cfg.get("show_settings_on_start", True):
        settings_done = threading.Event()
        saved_cfg = [cfg]

        def on_save(new_cfg):
            saved_cfg[0] = new_cfg
            settings_done.set()

        SettingsWindow(cfg, on_save=on_save, first_run=is_first)
        cfg = saved_cfg[0]

        # 如果用户直接关掉设置窗口且没有WiFi配置则退出
        if not cfg.get("target_wifis"):
            sys.exit(0)

    log(f"启动追踪器，监控WiFi: {cfg['target_wifis']}")
    TrayApp(cfg)

if __name__ == "__main__":
    main()
