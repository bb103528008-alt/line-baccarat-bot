
LINE 賭桌記帳機器人

功能：
- 固定倍率 x300
- 多人同時計算
- 自動加減分
- 歷史紀錄
- 銀行資金紀錄
- LINE 群組使用

安裝：

1. 安裝套件
pip install flask line-bot-sdk

2. 建立 LINE BOT
https://developers.line.biz/

3. 替換 app.py 內：
YOUR_CHANNEL_ACCESS_TOKEN
YOUR_CHANNEL_SECRET

4. 啟動
python app.py

5. 使用 ngrok
https://ngrok.com/

ngrok http 5000

Webhook:
https://你的網址/callback

指令：

+20 胖
-30 浩

/查詢
/歷史
/銀行 5000
