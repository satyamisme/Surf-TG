# import logging # LOGGER from bot will be used
from aiohttp.web import Application
from cryptography.fernet import Fernet
from aiohttp_session import setup
from aiohttp_session.cookie_storage import EncryptedCookieStorage
# from aiohttp_csrf import setup_csrf, SessionPolicy # Removed

from bot.server.stream_routes import routes
from bot.config import Telegram
from bot import LOGGER # Import LOGGER

async def web_server():
    if not Telegram.SESSION_SECRET_KEY:
        LOGGER.critical("SESSION_SECRET_KEY is not configured!")
        raise ValueError("SESSION_SECRET_KEY is not configured!")
    
    secret_key_bytes = Telegram.SESSION_SECRET_KEY.encode('utf-8')
    
    web_app = Application(client_max_size=30000000)
    # Session setup
    setup(web_app, EncryptedCookieStorage(Fernet(secret_key_bytes)))

    # CSRF Protection Setup (Reverted)
    # if not Telegram.CSRF_SECRET_KEY:
    #     LOGGER.critical("CSRF_SECRET_KEY is not configured! Exiting.")
    #     raise ValueError("CSRF_SECRET_KEY is not configured!")
    # 
    # setup_csrf(
    #     web_app,
    #     secret_key=Telegram.CSRF_SECRET_KEY.encode('utf-8'), # Ensure it's bytes
    #     policy_class=SessionPolicy # Store CSRF token in session
    # )

    web_app.add_routes(routes)
    return web_app
