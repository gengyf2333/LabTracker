# 实验室工作时长追踪器

自动检测 WiFi → 记录工作时长 → 浏览器可视化热力图

---

## 文件结构

```
E:/Coin Laundry/LabTracker/files/
  ├── data/
  │     └── data.json          ← 工时数据（自动生成）
  ├── log/
  │     └── tracker.log        ← 运行日志
  ├── lab_tracker_app_2.py     ← 主程序
  ├── lab_dashboard.html       ← 可视化页面
  ├── build_exe.bat            ← 打包为 exe
  └── config.json              ← 设置（自动生成）
```

---

## 使用方式

### 启动追踪器

```powershell
pythonw "E:\Coin Laundry\LabTracker\files\lab_tracker_app_2.py"
```

首次运行会弹出设置窗口。之后根据设置决定是否每次启动都弹出。

### 查看 Dashboard

另开一个终端，启动本地服务器：

```powershell
cd "E:\Coin Laundry\LabTracker\files"
python -m http.server 8080
```

浏览器打开：
```
http://localhost:8080/lab_dashboard.html
```

---

## 功能说明

### 追踪器（lab_tracker_app_2.py）

**WiFi 自动检测**
- 每 30 秒检测一次当前 WiFi
- 连上目标 WiFi → 自动开始计时
- 断开 WiFi → 自动结束并保存当次会话
- 会话按开始时间的日期归档（不会因为跨天记到第二天）

**实时写入**
- 进行中的会话每 5 分钟写入一次临时数据（带 `_temp` 标记）
- 不需要断开 WiFi，Dashboard 就能看到最新进度
- 重新启动时临时数据自动转为正式记录，不丢数据

**右下角状态条**
- 绿点：正在记录中，显示当前 WiFi 名和已记录时长
- 灰点：等待连接实验室 WiFi
- ⚙ 按钮：打开设置窗口
- ✕ 按钮：退出程序（退出前自动保存当前会话）
- 状态条可拖动位置

**设置窗口**
- 扫描附近 WiFi 直接选择，或手动输入 WiFi 名称
- 支持添加多个目标 WiFi
- 可选：每次启动是否弹出设置窗口
- 可选：开机自动启动（写入注册表）

**开机自启**
- 勾选后写入 HKCU\Software\Microsoft\Windows\CurrentVersion\Run
- 使用 pythonw 启动，不显示命令行窗口
- WiFi 检测使用 CREATE_NO_WINDOW，不会周期性闪烁黑窗口

---

### Dashboard（lab_dashboard.html）

**统计卡片**
- 本周工时、本月工时（过去30天）、总计工时、工作日平均

**热力图**
- GitHub 风格，过去一年每天的工时
- 颜色深浅对应当天工时多少
- 鼠标悬停显示具体日期和工时
- 支持 6 种主题颜色：绿、蓝、紫、橙、粉、青

**今日会话**
- 显示今天每次连接记录的开始时间、结束时间、时长

**近 6 周汇总**
- 每周工作天数、总工时、最长单日工时

**数据读取**
- 所有统计从 sessions 实时计算，不依赖 daily.total
- 手动在 data.json 里添加 session 条目即可生效
- 每 60 秒自动刷新，Ctrl+Shift+R 可强制刷新

---

## 数据格式

`data/data.json` 结构：

```json
{
  "daily": {
    "2026-05-26": {"total": 3.57}
  },
  "sessions": [
    {
      "date": "2026-05-26",
      "start": "2026-05-26T14:44",
      "end": "2026-05-26T15:25",
      "hours": 0.68,
      "wifi": "ICELAB_5G"
    }
  ]
}
```

手动添加工时：直接在 sessions 数组里加一条记录，daily.total 不需要同步修改，Dashboard 会自动从 sessions 计算。

---

## 打包为 exe

双击 `build_exe.bat`，完成后 `dist\LabTracker.exe` 即为可执行文件。

---

## 待办

- 本地服务器并入开机自启（目前需要手动启动）
- 设置窗口中配置 WiFi 对应的显示颜色
- 周报功能完善