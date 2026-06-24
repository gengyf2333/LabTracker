import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

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
