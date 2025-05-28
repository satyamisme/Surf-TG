from asyncio import get_event_loop, sleep as asleep, gather
from traceback import format_exc
import pymongo.errors # Added for database error handling
# import sys # Not using sys.exit() for now, return is sufficient

from aiohttp import web
from pyrogram import idle

from bot import __version__, LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.server import web_server
from bot.telegram import StreamBot, UserBot
from bot.telegram.clients import initialize_clients

loop = get_event_loop()

async def start_services():
    LOGGER.info(f'Initializing Surf-TG v-{__version__}')
    await asleep(1.2)

    # Initialize and sync database configuration
    db_instance = None # Define db_instance to ensure it's available if needed later
    try:
        LOGGER.info("Initializing database connection...")
        # Database is already imported: from bot.helper.database import Database
        db_instance = Database()
        await db_instance.sync_config_from_env()
        LOGGER.info("Database connection successful and configuration synced.")
        # If db_instance needs to be passed to other functions called from here, it can be.
        # Current structure suggests other modules create their own instances.
    except pymongo.errors.ServerSelectionTimeoutError as e:
        LOGGER.error(f"MongoDB server selection timed out: {e}. Please check your DATABASE_URL and network connectivity.")
        LOGGER.error("Bot cannot start without a valid database connection. Aborting startup.")
        return  # Stop further execution of start_services
    except pymongo.errors.ConnectionFailure as e:
        LOGGER.error(f"Failed to connect to MongoDB: {e}. Please check your DATABASE_URL and network connectivity.")
        LOGGER.error("Bot cannot start without a valid database connection. Aborting startup.")
        return  # Stop further execution of start_services
    except Exception as e:
        LOGGER.error(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        LOGGER.error("Bot cannot start due to database initialization error. Aborting startup.")
        return  # Stop further execution of start_services
    
    # At this point, db_instance holds the Database object if initialization was successful.
    # However, based on existing code (e.g., plugins/start.py), other parts of the application
    # instantiate their own Database objects. So, db_instance here was primarily for the initial sync.

    await StreamBot.start()
    StreamBot.username = StreamBot.me.username
    LOGGER.info(f"Bot Client : [@{StreamBot.username}]")
    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.start()
        UserBot.username = UserBot.me.username or UserBot.me.first_name or UserBot.me.id
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
    await StreamBot.stop()
    if len(Telegram.SESSION_STRING) != 0:
        await UserBot.stop()


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
