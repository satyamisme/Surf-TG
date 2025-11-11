import logging
import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session
from bot.helper.database import Database
from bot.helper.chats import get_chats, post_playlist, posts_chat, posts_db_file
from bot.config import Telegram
from bot.server.stream_server import media_streamer

routes = web.RouteTableDef()

@routes.get('/login')
async def login_get(request):
    session = await get_session(request)
    redirect_url = session.get('redirect_url', '/home')
    return aiohttp_jinja2.render_template('login.html', request, {'redirect_url': redirect_url})

@routes.post('/login')
async def login_post(request):
    session = await get_session(request)
    data = await request.post()
    username = data.get('username')
    password = data.get('password')

    if ((username == Telegram.USERNAME and password == Telegram.PASSWORD) or
        (username == Telegram.ADMIN_USERNAME and password == Telegram.ADMIN_PASSWORD)):
        session['user'] = username
        redirect_url = session.pop('redirect_url', '/home')
        return web.HTTPFound(redirect_url)
    else:
        return aiohttp_jinja2.render_template('login.html', request, {'msg': "Invalid credentials"})

@routes.get('/home')
async def home_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        db = request.app['db']
        channels = await get_chats()
        phtml = await posts_chat(channels)
        playlists = await db.get_Dbfolder('root')
        dhtml = await post_playlist(playlists)
        is_admin = (user == Telegram.ADMIN_USERNAME)

        return aiohttp_jinja2.render_template('home.html', request, {
            'channels': channels,
            'playlists': playlists,
            'is_admin': is_admin
        })
    except Exception as e:
        logging.exception("Error in home page")
        return web.Response(text="Internal Server Error", status=500)

@routes.get('/search')
async def search_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        db = request.app['db']
        query = request.query.get('q', '').strip()

        try:
            page = max(1, int(request.query.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        if not query or len(query) < 2:
            results = []
        else:
            results = await db.search_files(query, page)

        return aiohttp_jinja2.render_template('search.html', request, {
            'query': query,
            'search_results': results
        })
    except Exception as e:
        logging.exception(f"Search page error for query '{query}': {e}")
        return web.Response(text=f"Internal Server Error: Unable to process search", status=500)

@routes.get('/playlist')
async def playlist_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        db = request.app['db']
        parent = request.query.get('db', 'root')

        try:
            page = max(1, int(request.query.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        playlists = await db.get_Dbfolder(parent, page=page)
        files = await db.get_dbFiles(parent, page=page)
        text = await db.get_info(parent)

        dhtml = await post_playlist(playlists)
        dphtml = await posts_db_file(files)
        is_admin = (user == Telegram.ADMIN_USERNAME)

        return aiohttp_jinja2.render_template('playlist.html', request, {
            'current_folder_name': text,
            'folders': playlists,
            'files': files,
            'page': page,
            'current_folder_id': parent,
            'is_admin': is_admin
        })
    except Exception:
        logging.exception("Error in playlist page")
        return web.Response(text="Internal Server Error", status=500)

@routes.get("/stream/{encodedname}")
async def stream_handler(request):
    return await media_streamer(request)

@routes.get('/rchatid/{encodedname}')
async def video_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        encodedname = request.match_info['encodedname']
        message_id = request.query.get('id')
        secure_hash = request.query.get('hash')

        return aiohttp_jinja2.render_template('video.html', request, {
            'encodedname': encodedname,
            'message_id': message_id,
            'secure_hash': secure_hash,
            'base_url': Telegram.BASE_URL
        })
    except Exception:
        logging.exception("Error in video page")
        return web.Response(text="Internal Server Error", status=500)

@routes.get('/channels')
async def channels_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        channels = await get_chats()
        return aiohttp_jinja2.render_template('channels.html', request, {'channels': channels})
    except Exception:
        logging.exception("Channels page error")
        return web.Response(text="Internal server error", status=500)

@routes.get('/settings')
async def settings_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        return aiohttp_jinja2.render_template('settings.html', request, {})
    except Exception:
        logging.exception("Settings page error")
        return web.Response(text="Internal server error", status=500)

@routes.get('/api/stats/global')
async def global_stats(request):
    db = request.app['db']
    total_files = await db.get_total_indexed_files()
    channel_stats = await db.get_channel_stats()
    total_channels = len(channel_stats)

    total_storage = sum(channel.get('total_size', 0) for channel in channel_stats)

    return web.json_response({
        'total_files': total_files,
        'total_channels': total_channels,
        'total_storage_gb': round(total_storage / (1024**3), 2)
    })

@routes.get('/api/index/stats/{chat_id}')
async def index_stats(request):
    chat_id = request.match_info['chat_id']
    db = request.app['db']
    stats = await db.get_index_stats(chat_id)
    return web.json_response(stats)

@routes.post('/api/index/start/{chat_id}')
async def start_indexing(request):
    chat_id = request.match_info['chat_id']
    # Placeholder for starting the indexing process
    return web.json_response({'status': 'indexing_started', 'chat_id': chat_id})

@routes.post('/api/index/stop/{chat_id}')
async def stop_indexing(request):
    chat_id = request.match_info['chat_id']
    # Placeholder for stopping the indexing process
    return web.json_response({'status': 'indexing_stopped', 'chat_id': chat_id})

@routes.get('/{tail:.*}')
async def catch_all_404(request):
    return web.Response(text="404 Not Found", status=404)
