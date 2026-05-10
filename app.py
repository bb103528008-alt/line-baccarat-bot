
from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = "W9DMNdyysRVmJ4U/8YybbaYMNGU2kKpivuKtUA2BX/qByTD+vBDIOUtrBoV8Ryx7+Yaj8AIjqCUevB8D/LDNcF3OHYHqanIEUyw8AxQQrNPWOqHNYbZlAANWKnkSvHic8asFadMs8IcZbJArcPNvQAdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "e4e27260b79a6c4942b559daed99c241"

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
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount INTEGER,
            final_amount INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bank (
            id INTEGER PRIMARY KEY,
            total INTEGER DEFAULT 0
        )
    """)

    c.execute("INSERT OR IGNORE INTO bank (id, total) VALUES (1, 0)")
    conn.commit()
    conn.close()

def update_score(name, amount):
    final_amount = amount * RATE

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT score FROM scores WHERE name=?", (name,))
    row = c.fetchone()

    if row:
        new_score = row[0] + final_amount
        c.execute("UPDATE scores SET score=? WHERE name=?", (new_score, name))
    else:
        c.execute("INSERT INTO scores (name, score) VALUES (?, ?)", (name, final_amount))

    c.execute(
        "INSERT INTO history (name, amount, final_amount, created_at) VALUES (?, ?, ?, ?)",
        (name, amount, final_amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

def get_scores():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT name, score FROM scores ORDER BY score DESC")
    rows = c.fetchall()

    c.execute("SELECT total FROM bank WHERE id=1")
    bank = c.fetchone()[0]

    conn.close()

    result = []

    for name, score in rows:
        sign = "+" if score >= 0 else ""
        result.append(f"{name} {sign}{score}")

    result.append("")
    result.append(f"銀行 {bank}")

    return "\n".join(result)

def add_bank(amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("UPDATE bank SET total = total + ? WHERE id=1", (amount,))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT name, amount, final_amount, created_at
        FROM history
        ORDER BY id DESC
        LIMIT 10
    """)

    rows = c.fetchall()
    conn.close()

    result = ["最近10筆紀錄："]

    for row in rows:
        result.append(
            f"{row[3]} | {row[0]} {row[1]} => {row[2]}"
        )

    return "\n".join(result)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"

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
        
    if text == "/排行榜":
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT name, score FROM scores ORDER BY score DESC")
        rows = c.fetchall()

        conn.close()

        result = []
        result.append("🏆｜排行榜")
        result.append("━━━━━━━━━━")

        for i, (name, score) in enumerate(rows, start=1):
            sign = "+" if score >= 0 else ""

            medal = "🥇"
            if i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            elif i > 3:
                medal = f"{i}."

            result.append(
                f"{medal} {name}\n💰 {sign}{score}"
            )

        result.append("━━━━━━━━━━")

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(result))
        )
        return

    if text.startswith("/銀行"):
        try:
            amount = int(text.split(" ")[1])
            add_bank(amount)

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"銀行增加 {amount}")
            )
        except:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="格式錯誤：/銀行 5000")
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

            results.append(f"{name} {sign}{final_amount}")

    if results:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(results))
        )

if __name__ == "__main__":
    init_db()
    app.run(port=5000)
