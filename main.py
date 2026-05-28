import pyromod.listen
from config import Config
from pyrogram import Client, idle
import asyncio
from logger import LOGGER
from modules.retasks import recover_incomplete_batches
from modules.scheduler import start_daily_schedulers
from flask import Flask
import threading
import os

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Classplus Auto Uploader Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    # FIX: If port is in use (e.g. Colab already uses 8080), try next available port
    import socket
    for try_port in [port, 8081, 8082, 8000, 5000]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', try_port)) != 0:
                port = try_port
                break
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)

if __name__ == "__main__":
    bot = Client(
        "ClassplusAutoBot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=30,
        plugins=dict(root="plugins"),
        workers=1000,
    )

    async def main():
        await bot.start()
        bot_info = await bot.get_me()
        LOGGER.info(f"<--- @{bot_info.username} Started --->")
        asyncio.create_task(recover_incomplete_batches(bot))
        asyncio.create_task(start_daily_schedulers(bot))
        LOGGER.info("Daily update schedulers started")
        await idle()

    # Start Flask in background thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    asyncio.get_event_loop().run_until_complete(main())
    LOGGER.info("<--- Bot Stopped --->")
