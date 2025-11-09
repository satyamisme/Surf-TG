from time import time
from logging import getLogger, FileHandler, StreamHandler, INFO, ERROR, basicConfig
import asyncio

# Try to install uvloop and bind a loop immediately
try:
    import uvloop
    uvloop.install()
    # Explicitly create and set the loop so it's available early
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("✅ uvloop installed and event loop initialized globally.")
except Exception as e:
    print(f"⚠️ uvloop not available: {e}")

# Configure logging
basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    datefmt="%d-%b-%y %I:%M:%S %p",
    handlers=[FileHandler('log.txt'), StreamHandler()],
    level=INFO
)

getLogger("aiohttp").setLevel(ERROR)
getLogger("pyrogram").setLevel(ERROR)
getLogger("aiohttp.web").setLevel(ERROR)

LOGGER = getLogger(__name__)
StartTime = time()

__version__ = "1.2.6"
