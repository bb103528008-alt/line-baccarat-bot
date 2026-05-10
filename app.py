from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import sqlite3
import re
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "W9DMNdyysRVmJ4U/8YybbaYMNGU2kKpivuKtUA2BX/qByTD+vBDIOUtrBoV8Ryx7+Yaj8AIjqCUevB8D/LDNcF3OHYHqanIEUyw8AxQQrNPWOqHNYbZlAANWKnkSvHic8asFadMs8IcZbJArcPNvQAdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "e4e27260b79a6c4942b559daed99c241"
GROUP_ID = "Cbeda1170fc219e760eb34acb861408bd"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

DB_NAME = "game.db"
RATE = 300

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            name TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_scores (
            name TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount INTEGER,
            final_amount INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def update_score(name, amount):
    final_amount = amount * RATE

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT score FROM scores WHERE name=?", (name,))
    row = c.fetchone()

    if row:
        c.execute(
            "UPDATE scores SET score=? WHERE name=?",
            (row[0] + final_amount, name)
        )
    else:
        c.execute(
            "INSERT INTO scores (name, score) VALUES (?, ?)",
            (name, final_amount)
        )

    c.execute("SELECT score FROM daily_scores WHERE name=?", (name,))
    daily_row = c.fetchone()

    if daily_row:
        c.execute(
            "UPDATE daily_scores SET score=? WHERE name=?",
            (daily_row[0] + final_amount, name)
        )
    else:
        c.execute(
            "INSERT INTO daily_scores (name, score) VALUES (?, ?)",
            (name, final_amount)
        )

    c.execute(
        "INSERT INTO history (name, amount, final_amount, created_at) VALUES (?, ?, ?, ?)",
        (
            name,
            amount,
            final_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()

def get_scores():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, score FROM scores ORDER BY score DESC")
    rows = c.fetchall()

    conn.close()

    if not rows:
        return "目前沒有資料"

    result = []

    for name, score in rows:
        sign = "+" if score >= 0 else ""
        result.append(f"{name}：{sign}{score}")

    return "\n".join(result)

def get_daily_scores():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, score FROM daily_scores ORDER BY score DESC")
    rows = c.fetchall()

    conn.close()

    if not rows:
        return "目前沒有資料"

    result = ["📊｜今日排行", "━━━━━━━━━━"]

    for i, (name, score) in enumerate(rows, start=1):
        sign = "+" if score >= 0 else ""

        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        result.append(f"{medal} {name}\n💰 {sign}{score}\n")

    result.append("━━━━━━━━━━")

    return "\n".join(result)

def get_total_ranking():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, score FROM scores ORDER BY score DESC")
    rows = c.fetchall()

    conn.close()

    if not rows:
        return "目前沒有資料"

    result = ["👑｜總排行（累計）", "━━━━━━━━━━"]

    for i, (name, score) in enumerate(rows, start=1):
        sign = "+" if score >= 0 else ""

        if i == 1:
            medal = "🥇"
        elif i == 2:
            medal = "🥈"
        elif i == 3:
            medal = "🥉"
        else:
            medal = f"{i}."

        result.append(f"{medal} {name}\n💰 {sign}{score}\n")

    result.append("━━━━━━━━━━")

    return "\n".join(result)

def get_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT name, amount, final_amount, created_at FROM history ORDER BY id DESC LIMIT 20"
    )

    rows = c.fetchall()

    conn.close()

    if not rows:
        return "目前沒有歷史紀錄"

    result = []

    for name, amount, final_amount, created_at in rows:
        sign = "+" if final_amount >= 0 else ""

        result.append(
            f"{created_at}\n{name} {amount:+}\n💰 {sign}{final_amount}\n"
        )

    return "\n".join(result)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    

    
    text = event.message.text.strip()

    if text == "/查詢":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_scores())
        )
        return

    if text == "/歷史":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_history())
        )
        return

    if text == "/今日排行":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_daily_scores())
        )
        return

    if text == "/總排行":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_total_ranking())
        )
        return

    if text.startswith("/刪除"):
        try:
            name = text.split(" ")[1]

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()

            c.execute("DELETE FROM scores WHERE name=?", (name,))
            c.execute("DELETE FROM daily_scores WHERE name=?", (name,))
            c.execute("DELETE FROM history WHERE name=?", (name,))

            conn.commit()
            conn.close()

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"已刪除 {name} 的所有資料")
            )

        except:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤：/刪除 名字")
            )

        return

    lines = text.split("\n")
    results = []

    for line in lines:
        match = re.match(r"([+-]?\d+)\s+(.+)", line.strip())

        if match:
            amount = int(match.group(1))
            name = match.group(2)

            update_score(name, amount)

            final_amount = amount * RATE
            sign = "+" if final_amount >= 0 else ""

            results.append(f"{name}\n💰 {sign}{final_amount}")

    if results:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n\n".join(results))
        )

def auto_daily_report():
    if GROUP_ID == "你的群組ID":
        return

    message = get_daily_scores() + "\n\n" + get_total_ranking()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    current_day = datetime.now().day

    if current_day == 1:
        c.execute(
            "SELECT name, score FROM scores ORDER BY score ASC LIMIT 1"
        )

        loser = c.fetchone()

        if loser:
            message += f"\n\n💀｜本月最輸玩家\n━━━━━━━━━━\n😭 {loser[0]}\n💸 {loser[1]}"

    line_bot_api.push_message(
        GROUP_ID,
        TextSendMessage(text=message)
    )

    c.execute("DELETE FROM daily_scores")

    conn.commit()
    conn.close()

scheduler = BackgroundScheduler()

scheduler.add_job(
    auto_daily_report,
    'cron',
    hour=0,
    minute=0
)

scheduler.start()

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
