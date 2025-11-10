from os import path as ospath
from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database
from bot.helper.exceptions import InvalidHash
from bot.helper.file_size import get_readable_file_size
from bot.server.file_properties import get_file_ids
from bot.telegram import StreamBot
import re

db = Database()

async def render_page(id, secure_hash, chat_id=None, html=None, playlist=None,
                     database=None, route='home', redirect_url=None, msg=None,
                     is_admin=False, channels=None, search_results=None, query=None, encodedname=None):

    theme = await db.get_variable('theme') or Telegram.THEME
    t_path = ospath.join('bot', 'server', 'templates')

    try:
        if route == 'login':
            with open(ospath.join(t_path, 'login.html'), 'r') as f:
                template = f.read()
            return template.replace('{{ msg }}', msg or '')

        with open(ospath.join(t_path, 'base.html'), 'r') as f:
            base_template = f.read()

        content = ''
        if route == 'home':
            with open(ospath.join(t_path, 'home.html'), 'r') as f:
                content = f.read()

        elif route == 'playlist':
            with open(ospath.join(t_path, 'playlist.html'), 'r') as f:
                content = f.read()

        elif route == 'channels':
            with open(ospath.join(t_path, 'channels.html'), 'r') as f:
                content = f.read()

        elif route == 'search':
            with open(ospath.join(t_path, 'search.html'), 'r') as f:
                content = f.read()

        elif route == 'video':
            with open(ospath.join(t_path, 'video.html'), 'r') as f:
                content = f.read()

        base_template = base_template.replace('{% block content %}', content)
        base_template = base_template.replace('{% block title %}', f"Surf-TG - {msg or 'Home'}")

        return base_template

    except FileNotFoundError:
        return "<h1>Template not found</h1><p>Please check template paths.</p>"
    except Exception as e:
        LOGGER.error(f"Template render error: {e}")
        return "<h1>Render Error</h1>"
