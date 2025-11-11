from asyncio import sleep as asleep, gather
from pyrogram import Client
from bot import LOGGER
from bot.config import Telegram
from bot.helper.parser import TokenParser

multiclients = {}
workloads = {}
StreamBot = None

async def initialize_clients():
    global StreamBot
    multiclients.clear()
    workloads.clear()
    StreamBot = None

    all_tokens = TokenParser.parse_from_env()
    if not all_tokens:
        LOGGER.info("No additional Bot Clients found, Using default client")
        return

    async def start_client(client_id, token):
        try:
            LOGGER.info(f"Starting - Bot Client {client_id}")
            await asleep(2)
            client = Client(
                name=str(client_id),
                api_id=Telegram.API_ID,
                api_hash=Telegram.API_HASH,
                bot_token=token,
                sleep_threshold=Telegram.SLEEP_THRESHOLD,
                no_updates=True,
                in_memory=True,
            )
            await client.start()
            me = await client.get_me()
            LOGGER.info(f"Client {client_id} started as {me.username}")
            return client_id, client
        except Exception as e:
            LOGGER.error(f"Failed starting Client - {client_id} Error: {e}", exc_info=True)
            return client_id, None

    clients_list = await gather(*[start_client(i, token) for i, token in all_tokens.items()])
    for client_id, client in clients_list:
        if client:
            multiclients[client_id] = client
            if StreamBot is None and client_id == 0:
                StreamBot = client
    if len(multiclients) != 1:
        Telegram.MULTI_CLIENT = True
        LOGGER.info(f"Multi Client Initialized: {len(multiclients)} clients")
