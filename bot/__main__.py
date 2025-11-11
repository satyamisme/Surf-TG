import base64
import os
import asyncio
import secrets
import aiohttp_jinja2
import jinja2
from aiohttp import web
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from bot.server.stream_routes import routes
from bot.helper.database import Database
from bot.config import Telegram
from bot import LOGGER
from bot.telegram import StreamBot, UserBot
from bot.telegram.clients import initialize_clients

async def start_services():
    session_secret = os.environ.get("SESSION_SECRET")
    if session_secret:
        SECRET_KEY = base64.urlsafe_b64decode(session_secret)
    else:
        SECRET_KEY = secrets.token_bytes(32)

    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('bot/server/templates'))
    setup(app, EncryptedCookieStorage(SECRET_KEY))
    app['db'] = Database()
    app.router.add_routes(routes)
    app.router.add_static('/static', path='bot/server/static', name='static')

    LOGGER.info(f"Initializing Surf-TG v-{Telegram.VERSION}")

    await StreamBot.start()
    me = await StreamBot.get_me()
    LOGGER.info(f"Bot Client {me.username} started")

    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.start()
        user_me = await UserBot.get_me()
        LOGGER.info(f"User Client {user_me.username or user_me.first_name or user_me.id} started")

    await initialize_clients()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Telegram.PORT)
    await site.start()
    return app

async def stop_services():
    try:
        await StreamBot.stop()
    except ConnectionError as e:
        if "Client is already terminated" in str(e):
            LOGGER.info("StreamBot already terminated.")
        else:
            raise
    try:
        await UserBot.stop()
    except ConnectionError as e:
        if "Client is already terminated" in str(e):
            LOGGER.info("UserBot already terminated.")
        else:
            raise

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        app = loop.run_until_complete(start_services())
        loop.run_forever()
    except Exception as e:
        LOGGER.critical(f"Unhandled exception: {e}", exc_info=True)
    finally:
        loop.run_until_complete(stop_services())
