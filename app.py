from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import sqlite3
import re
from datetime import datetime

app = Flask(__name__)

# =========================
# LINE TOKEN
# =========================

LINE_CHANNEL_ACCESS_TOKEN = "W9DMNdyysRVmJ4U/8YybbaYMNGU2kKpivuKtUA2BX/qByTD+vBDIOUtrBoV8Ryx7+Yaj8AIjqCUevB8D/LDNcF3OHYHqanIEUyw8AxQQrNPWOqHNYbZlAANWKnkSvHic8asFadMs8IcZbJArcPNvQAdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "e4e27260b79a6c4942b559daed99c241"
GROUP_ID = "Cbeda1170fc219e760eb34acb861408bd"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

DB_NAME = "game.db"
RATE = 300


# =========================
# DB
# =========================

def get_conn():
    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False,
        timeout=30
    )

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    return conn


# =========================
# 初始化資料庫
# =========================

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            name TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_scores (
            name TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            amount INTEGER,
            final_amount INTEGER,
            created_at TEXT
        )
    ''')

    conn.commit()
    c.close()
    conn.close()


# =========================
# 更新分數
# =========================

def update_score(name, amount):
    final_amount = amount * RATE

    conn = get_conn()
    c = conn.cursor()

    # 總排行
    c.execute(
        "SELECT score FROM scores WHERE name=?",
        (name,)
    )

    row = c.fetchone()

    if row:
        new_score = row[0] + final_amount

        c.execute(
            "UPDATE scores SET score=? WHERE name=?",
            (new_score, name)
        )
    else:
        c.execute(
            "INSERT INTO scores (name, score) VALUES (?, ?)",
            (name, final_amount)
        )

    # 今日排行
    c.execute(
        "SELECT score FROM daily_scores WHERE name=?",
        (name,)
    )

    daily_row = c.fetchone()

    if daily_row:
        daily_score = daily_row[0] + final_amount

        c.execute(
            "UPDATE daily_scores SET score=? WHERE name=?",
            (daily_score, name)
        )
    else:
        c.execute(
            "INSERT INTO daily_scores (name, score) VALUES (?, ?)",
            (name, final_amount)
        )

    # 歷史紀錄
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
    c.close()
    conn.close()


# =========================
# 查詢
# =========================

def get_scores():
    conn = get_conn()
    c = conn.cursor()

    c.execute(
        "SELECT name, score FROM scores ORDER BY score DESC"
    )

    rows = c.fetchall()

    conn.close()

    if not rows:
        return "目前沒有資料"

    result = []

    for name, score in rows:
        sign = "+" if score >= 0 else ""
        result.append(f"{name}：{sign}{score}")

    return "\n".join(result)


# =========================
# 歷史
# =========================

def get_history():
    conn = get_conn()
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


# =========================
# CALLBACK
# =========================

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)

    except InvalidSignatureError:
        return 'Invalid signature', 400

    return 'OK'


# =========================
# MESSAGE
# =========================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    text = event.message.text.strip()

    # 查詢
    if text == "/查詢":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_scores())
        )
        return

    # 歷史
    if text == "/歷史":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=get_history())
        )
        return

    # 今日排行
    if text == "/今日排行":

        conn = get_conn()
        c = conn.cursor()

        c.execute(
            "SELECT name, score FROM daily_scores ORDER BY score DESC"
        )

        rows = c.fetchall()
        conn.close()

        result = ["📊 今日排行", "━━━━━━━━━━"]

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

            result.append(
                f"{medal} {name}\n💰 {sign}{score}\n"
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(result))
        )

        return

    # 總排行
    if text == "/總排行":

        conn = get_conn()
        c = conn.cursor()

        c.execute(
            "SELECT name, score FROM scores ORDER BY score DESC"
        )

        rows = c.fetchall()
        conn.close()

        result = ["👑 總排行", "━━━━━━━━━━"]

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

            result.append(
                f"{medal} {name}\n💰 {sign}{score}\n"
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n".join(result))
        )

        return

    # 銀行
    if text.startswith("/銀行"):

        try:
            amount = int(text.split(" ")[1])

            conn = get_conn()
            c = conn.cursor()

            c.execute(
                "SELECT score FROM scores WHERE name='銀行'"
            )

            row = c.fetchone()

            if row:
                c.execute(
                    "UPDATE scores SET score=? WHERE name='銀行'",
                    (row[0] + amount,)
                )
            else:
                c.execute(
                    "INSERT INTO scores (name, score) VALUES (?, ?)",
                    ("銀行", amount)
                )

            conn.commit()
            c.close()
            conn.close()

            sign = "+" if amount >= 0 else ""

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"🏦 銀行更新\n💰 {sign}{amount}")
            )

        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"銀行失敗\n{str(e)}")
            )

        return

    # 提領
    if text.startswith("/提領"):

        try:
            parts = text.split(" ")

            name = parts[1]
            amount = int(parts[2])

            conn = get_conn()
            c = conn.cursor()

            c.execute(
                "SELECT score FROM scores WHERE name=?",
                (name,)
            )

            row = c.fetchone()

            if not row:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="找不到玩家")
                )
                return

            c.execute(
                "UPDATE scores SET score=? WHERE name=?",
                (row[0] - amount, name)
            )

           conn.commit()
            c.close()
            conn.close()

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"💸 提領成功\n{name}\n-{amount}")
            )

        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"提領失敗\n{str(e)}")
            )

        return

    # 結帳
    if text.startswith("/結帳"):

        try:
            parts = text.split(" ")

            name = parts[1]
            amount = int(parts[2])

            conn = get_conn()
            c = conn.cursor()

            c.execute(
                "SELECT score FROM scores WHERE name=?",
                (name,)
            )

            row = c.fetchone()

            if not row:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="找不到玩家")
                )
                return

            c.execute(
                "UPDATE scores SET score=? WHERE name=?",
                (row[0] - amount, name)
            )

            # 銀行增加
            c.execute(
                "SELECT score FROM scores WHERE name='銀行'"
            )

            bank_row = c.fetchone()

            if bank_row:
                c.execute(
                    "UPDATE scores SET score=? WHERE name='銀行'",
                    (bank_row[0] + amount,)
                )
            else:
                c.execute(
                    "INSERT INTO scores (name, score) VALUES (?, ?)",
                    ("銀行", amount)
                )

            conn.commit()
            c.close()
            conn.close()

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"🏦 結帳成功\n{name}\n💸 -{amount}")
            )

        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"結帳失敗\n{str(e)}")
            )

        return

    # 刪除
    if text.startswith("/刪除"):

        try:
            parts = text.split(" ", 1)

            if len(parts) < 2:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="格式錯誤：/刪除 名字")
                )
                return

            name = parts[1].strip()

            conn = get_conn()
            c = conn.cursor()

            c.execute(
                "DELETE FROM scores WHERE name=?",
                (name,)
            )

            c.execute(
                "DELETE FROM daily_scores WHERE name=?",
                (name,)
            )

            c.execute(
                "DELETE FROM history WHERE name=?",
                (name,)
            )

            conn.commit()
            c.close()
            conn.close()

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已刪除 {name}")
            )

        except Exception as e:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"刪除失敗\n{str(e)}")
            )

        return

    # 記帳
    lines = text.split("\n")

    results = []

    for line in lines:

        match = re.match(
            r"([+-]?\d+)\s+(.+)",
            line.strip()
        )

        if match:

            amount = int(match.group(1))
            name = match.group(2)

            update_score(name, amount)

            final_amount = amount * RATE

            sign = "+" if final_amount >= 0 else ""

            results.append(
                f"{name}\n💰 {sign}{final_amount}"
            )

    if results:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="\n\n".join(results))
        )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)