#!/usr/bin/env python3
import asyncio
import os
from traceback import format_exc

# Set event loop policy BEFORE importing anything else that uses asyncio
if os.name == 'nt':  # Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


async def main():
    # Now that the event loop is set, we can import the rest of the application
    from aiohttp import web
    from pyrogram import idle

    from bot import __version__, LOGGER
    from bot.config import Telegram
    from bot.server import web_server
    from bot.telegram import StreamBot, UserBot
    from bot.telegram.clients import initialize_clients

    LOGGER.info(f'Initializing Surf-TG v-{__version__}')
    await asyncio.sleep(1.2)

    # Start the Telegram bot client
    await StreamBot.start()
    StreamBot.username = StreamBot.me.username
    LOGGER.info(f"Bot Client : [@{StreamBot.username}]")

    # Start the user client if a session string is provided
    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.start()
        UserBot.username = UserBot.me.username or UserBot.me.first_name or UserBot.me.id
        LOGGER.info(f"User Client : {UserBot.username}")

    await asyncio.sleep(1.2)
    LOGGER.info("Initializing Multi Clients")
    await initialize_clients()

    # Start the web server
    await asyncio.sleep(2)
    LOGGER.info('Initalizing Surf Web Server..')
    server = web.AppRunner(await web_server())
    LOGGER.info("Server CleanUp!")
    await server.cleanup()

    await asyncio.sleep(2)
    LOGGER.info("Server Setup Started !")

    await server.setup()
    await web.TCPSite(server, '0.0.0.0', Telegram.PORT).start()

    LOGGER.info("Surf-TG Started Revolving !")
    await idle()

    # Stop clients after idle() is interrupted
    await StreamBot.stop()
    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception:
        # We need to import the logger here because it's only available after the imports in main()
        from bot import LOGGER
        LOGGER.error(format_exc())
