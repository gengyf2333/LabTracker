#!/usr/bin/env python3
"""
实验室工作时长追踪器
- 检测指定 WiFi 网络，自动开始/结束记录
- 每周一生成周报
- 数据存为 JSON，可用前端可视化
"""

import subprocess
import json
import time
import os
import platform
from datetime import datetime, date, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# 配置区：修改这里即可
# ─────────────────────────────────────────────
TARGET_WIFIS = [
    "LabNetwork_5G",
    "Lab_Secure",
    "SSID-B40D73",
    "ICELAB"
    # 在这里继续添加实验室 WiFi 名称
]

CHECK_INTERVAL = 30          # 每隔多少秒检测一次 WiFi（秒）
DATA_FILE = Path.home() / ".lab_tracker_data.json"
LOG_FILE  = Path.home() / ".lab_tracker.log"
# ─────────────────────────────────────────────

def get_current_wifi() -> str | None:
    """获取当前连接的 WiFi 名称，跨平台支持"""
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            result = subprocess.run(
                ["/System/Library/PrivateFrameworks/Apple80211.framework/"
                 "Versions/Current/Resources/airport", "-I"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if " SSID:" in line:
                    return line.split("SSID:")[-1].strip()

        elif system == "Linux":
            # 先尝试 nmcli
            result = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if line.startswith("yes:"):
                    return line.split(":", 1)[1].strip()

            # 备选：iwgetid
            result = subprocess.run(
                ["iwgetid", "-r"], capture_output=True, text=True, timeout=5
            )
            ssid = result.stdout.strip()
            return ssid if ssid else None

        elif system == "Windows":
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, timeout=5
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
                # 匹配 "SSID" 但排除 "BSSID"
                if line.startswith("SSID") and "BSSID" not in line and ":" in line:
                    ssid = line.split(":", 1)[1].strip()
                    return ssid if ssid else None

    except Exception as e:
        log(f"WiFi 检测出错: {e}")
    return None


def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": [], "daily": {}}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def date_key(d: date = None) -> str:
    return (d or date.today()).isoformat()


def add_hours_to_day(data: dict, day: str, hours: float, topic: str = "实验操作"):
    if day not in data["daily"]:
        data["daily"][day] = {"total": 0.0, "topics": {}}
    data["daily"][day]["total"] = round(data["daily"][day]["total"] + hours, 2)
    topics = data["daily"][day]["topics"]
    topics[topic] = round(topics.get(topic, 0.0) + hours, 2)


def weekly_report(data: dict) -> str:
    """生成上周的周报字符串"""
    today = date.today()
    # 找到上周一
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6)

    lines = [
        f"\n{'='*40}",
        f"📊 周报：{last_monday} ~ {last_sunday}",
        f"{'='*40}",
    ]
    week_total = 0.0
    topic_total: dict[str, float] = {}

    for i in range(7):
        day = last_monday + timedelta(days=i)
        key = date_key(day)
        day_data = data["daily"].get(key, {})
        hours = day_data.get("total", 0.0)
        week_total += hours
        weekday = ["一","二","三","四","五","六","日"][i]
        bar = "█" * int(hours) + ("▌" if hours % 1 >= 0.5 else "")
        lines.append(f"  周{weekday} {key}  {bar}  {hours:.1f}h")
        for topic, h in day_data.get("topics", {}).items():
            topic_total[topic] = topic_total.get(topic, 0.0) + h

    lines.append(f"\n  总计：{week_total:.1f} 小时")
    if topic_total:
        lines.append("  主题明细：")
        for t, h in sorted(topic_total.items(), key=lambda x: -x[1]):
            lines.append(f"    · {t}: {h:.1f}h")
    lines.append("="*40 + "\n")
    return "\n".join(lines)


def run():
    log("追踪器启动")
    log(f"监控 WiFi：{TARGET_WIFIS}")
    log(f"数据文件：{DATA_FILE}")

    data = load_data()
    session_start: datetime | None = None
    in_lab = False
    current_topic = "实验操作"
    last_report_week: int | None = None

    while True:
        now = datetime.now()
        wifi = get_current_wifi()
        connected_to_lab = wifi in TARGET_WIFIS

        # 进入实验室
        if connected_to_lab and not in_lab:
            in_lab = True
            session_start = now
            log(f"✅ 检测到 {wifi}，开始记录（主题：{current_topic}）")

        # 离开实验室
        elif not connected_to_lab and in_lab:
            in_lab = False
            if session_start:
                elapsed = (now - session_start).total_seconds() / 3600
                if elapsed > 0.05:  # 超过 3 分钟才记录
                    day = date_key(session_start.date())
                    add_hours_to_day(data, day, round(elapsed, 2), current_topic)
                    data["sessions"].append({
                        "date": day,
                        "start": session_start.isoformat(timespec="minutes"),
                        "end": now.isoformat(timespec="minutes"),
                        "hours": round(elapsed, 2),
                        "topic": current_topic,
                        "wifi": wifi or "unknown"
                    })
                    save_data(data)
                    log(f"⏹  会话结束，记录 {elapsed:.2f}h → {day}")
                session_start = None

        # 每周一自动生成上周周报
        if now.weekday() == 0:  # 周一
            week_num = now.isocalendar()[1]
            if last_report_week != week_num:
                report = weekly_report(data)
                print(report)
                log("已生成上周周报")
                last_report_week = week_num

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log("追踪器已手动停止")
