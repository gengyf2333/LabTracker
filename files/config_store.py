
# ═════════════════════════════════════════════════
# Config
# ═════════════════════════════════════════════════
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

BASE_DIR    = Path("E:/Coin Laundry/LabTracker/files")
CONFIG_FILE = BASE_DIR / "config.json"

# ── 默认配置 ──────────────────────────────────────
DEFAULT_CONFIG = {
    "target_wifis": [],
    "check_interval": 30,
    "show_settings_on_start": True,
    "autostart": False,
    "last_auto_report_week": None,
}

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
