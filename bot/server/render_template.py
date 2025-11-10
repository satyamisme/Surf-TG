from os import path as ospath
from bot import LOGGER
from bot.config import Telegram
from bot.helper.database import Database

db = Database()

async def render_page(id, secure_hash, chat_id=None, html=None, playlist=None,
                     database=None, route='home', redirect_url=None, msg=None,
                     is_admin=False, channels=None):

    theme = await db.get_variable('theme') or Telegram.THEME
    t_path = ospath.join('bot', 'server', 'templates')

    try:
        if route == 'login':
            with open(ospath.join(t_path, 'login.html'), 'r') as f:
                template = f.read()
            return template.replace('<!-- Error -->', msg or '').replace(
                '<!-- Theme -->', theme.lower()).replace(
                '<!-- RedirectURL -->', redirect_url or '/home')

        with open(ospath.join(t_path, 'base.html'), 'r') as f:
            base_template = f.read()

        if route == 'home':
            with open(ospath.join(t_path, 'home.html'), 'r') as f:
                content = f.read()
            content = content.replace('<!-- Chat ID -->', chat_id or '')
            content = content.replace('<!-- Print -->', html or '')

        elif route == 'video':
            file_data = await get_file_ids(StreamBot, chat_id=int(chat_id), message_id=int(id))
            if file_data.unique_id[:6] != secure_hash:
                LOGGER.info('Link hash: %s - %s', secure_hash,
                            file_data.unique_id[:6])
                LOGGER.info('Invalid hash for message with - ID %s', id)
                raise InvalidHash
            filename, tag, size = file_data.file_name, file_data.mime_type.split(
                '/')[0].strip(), get_readable_file_size(file_data.file_size)
            if filename is None:
                filename = "Proper Filename is Missing"
            filename = re.sub(r'[,|_\',]', ' ', filename)
            with open(ospath.join(t_path, 'video.html')) as r:
                poster = f"/api/thumb/{chat_id}?id={id}"
                content = (await r.read()).replace('<!-- Filename -->', filename).replace("<!-- Theme -->", theme.lower()).replace('<!-- Poster -->', poster).replace('<!-- Size -->', size).replace('<!-- Username -->', StreamBot.me.username)

        base_template = base_template.replace('{% block content %}', content)
        base_template = base_template.replace('{% block title %}', f"Surf-TG - {msg or 'Home'}")
        base_template = base_template.replace('{% if is_admin %}', 'style="display:block"' if is_admin else 'style="display:none"')

        return base_template

    except FileNotFoundError:
        return "<h1>Template not found</h1><p>Please check template paths.</p>"
    except Exception as e:
        LOGGER.error(f"Template render error: {e}")
        return "<h1>Render Error</h1>"
