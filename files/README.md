# 实验室工作时长追踪器

自动检测 WiFi → 记录工作时长 → 生成热力图周报

---

## 快速开始

### 1. 配置 WiFi 名称

打开 `lab_tracker.py`，修改顶部配置区：

```python
TARGET_WIFIS = [
    "你的实验室WiFi名",    # 改成实际的 SSID
    "备用WiFi名",
]
CHECK_INTERVAL = 30       # 检测频率（秒），建议 30~60
```

查看当前 WiFi 名：
- **macOS**: 点击菜单栏 WiFi 图标，或终端输入 `networksetup -getairportnetwork en0`
- **Linux**: 终端输入 `nmcli -t -f active,ssid dev wifi | grep yes`
- **Windows**: 终端输入 `netsh wlan show interfaces | findstr SSID`

---

### 2. 运行脚本

```bash
python3 lab_tracker.py
```

后台运行（macOS / Linux）：
```bash
nohup python3 lab_tracker.py > /dev/null 2>&1 &
```

---

### 3. 开机自动启动

**macOS（推荐用 launchd）**

创建 `~/Library/LaunchAgents/com.lab.tracker.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.lab.tracker</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/你的路径/lab_tracker.py</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/lab_tracker.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/lab_tracker_err.log</string>
</dict>
</plist>
```

加载：
```bash
launchctl load ~/Library/LaunchAgents/com.lab.tracker.plist
```

**Linux（systemd）**

创建 `/etc/systemd/user/lab-tracker.service`：

```ini
[Unit]
Description=Lab Work Tracker

[Service]
ExecStart=/usr/bin/python3 /你的路径/lab_tracker.py
Restart=always

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable lab-tracker
systemctl --user start lab-tracker
```

---

## 数据文件

数据保存在 `~/.lab_tracker_data.json`，格式如下：

```json
{
  "daily": {
    "2025-05-14": {
      "total": 6.5,
      "topics": {
        "实验操作": 4.0,
        "数据分析": 2.5
      }
    }
  },
  "sessions": [
    {
      "date": "2025-05-14",
      "start": "2025-05-14T09:00",
      "end": "2025-05-14T13:00",
      "hours": 4.0,
      "topic": "实验操作",
      "wifi": "LabNetwork_5G"
    }
  ]
}
```

---

## 切换主题

脚本本身不管颜色，颜色和热力图在前端可视化界面中切换。

若想在命令行手动记录（不依赖 WiFi 检测），可以直接编辑 JSON 数据文件。

---

## 依赖

- Python 3.10+（无需额外安装任何第三方库）
- macOS / Linux / Windows 均支持
