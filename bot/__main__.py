from bot import __version__, LOGGER
from asyncio import get_event_loop, sleep as asleep, gather
from traceback import format_exc

from aiohttp import web
from pyrogram import idle
from bot.config import Telegram
from bot.server import web_server
from bot.telegram import StreamBot, UserBot
from bot.telegram.clients import initialize_clients

loop = get_event_loop()

async def start_services():
    LOGGER.info(f'Initializing Surf-TG v-{__version__}')
    await asleep(1.2)

    await StreamBot.start()
    me = await StreamBot.get_me()
    StreamBot.username = me.username
    LOGGER.info(f"Bot Client : [@{StreamBot.username}]")
    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.start()
        user_me = await UserBot.get_me()
        UserBot.username = user_me.username or user_me.first_name or user_me.id
        LOGGER.info(f"User Client : {UserBot.username}")

    await asleep(1.2)
    LOGGER.info("Initializing Multi Clients")
    await initialize_clients()

    await asleep(2)
    LOGGER.info('Initalizing Surf Web Server..')
    server = web.AppRunner(await web_server())
    LOGGER.info("Server CleanUp!")
    await server.cleanup()

    await asleep(2)
    LOGGER.info("Server Setup Started !")

    await server.setup()
    await web.TCPSite(server, '0.0.0.0', Telegram.PORT).start()

    LOGGER.info("Surf-TG Started Revolving !")
    await idle()

async def stop_clients():
    try:
        await StreamBot.stop()
    except ConnectionError:
        pass
    try:
        if len(Telegram.SESSION_STRING) != 0:
            await UserBot.stop()
    except ConnectionError:
        pass


if __name__ == '__main__':
    try:
        loop.run_until_complete(start_services())
    except KeyboardInterrupt:
        LOGGER.info('Service Stopping...')
    except Exception:
        LOGGER.error(format_exc())
    finally:
        loop.run_until_complete(stop_clients())
        loop.stop()
