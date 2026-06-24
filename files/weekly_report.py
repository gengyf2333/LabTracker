
import random
from datetime import date, timedelta
from pathlib import Path


BASE_DIR = Path("E:/Coin Laundry/LabTracker/files")
LOG_DIR = BASE_DIR / "log"
LOG_DIR.mkdir(parents=True, exist_ok=True)


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
