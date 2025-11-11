import base64
import os
import asyncio
import secrets
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
    session_secret = os.environ.get('SESSION_SECRET')
    if session_secret:
        SECRET_KEY = base64.urlsafe_b64decode(session_secret)
    else:
        # Generate a new secret key if one isn't set
        SECRET_KEY = secrets.token_bytes(32)

    app = web.Application()

    # Setup session middleware with encrypted cookie storage
    setup(app, EncryptedCookieStorage(SECRET_KEY))

    # Attach the database instance to the application
    app['db'] = Database()

    # Register routes from stream_routes.py
    app.router.add_routes(routes)

    # Serve static files such as CSS, JS, images
    app.router.add_static('/static', path='bot/server/static', name='static')

    # Setup Web server runner
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', Telegram.PORT)
    await site.start()

    LOGGER.info(f"Surf-TG started on port {Telegram.PORT}")

    # Start bot clients
    await StreamBot.start()
    LOGGER.info(f"Bot Client {StreamBot.username} started")

    if Telegram.SESSION_STRING:
        await UserBot.start()
        LOGGER.info(f"User Client {UserBot.username} started")

    await initialize_clients()
    await asyncio.Event().wait()  # Keeps the app running

async def stop_services():
    await StreamBot.stop()
    if Telegram.SESSION_STRING:
        await UserBot.stop()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        LOGGER.info("Stopping Surf-TG...")
    finally:
        loop.run_until_complete(stop_services())
        loop.close()
