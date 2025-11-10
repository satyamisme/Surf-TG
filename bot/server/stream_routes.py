import logging
from aiohttp import web
from aiohttp_session import get_session
from bot.helper.database import Database
from bot.helper.chats import get_chats, post_playlist, posts_chat, posts_db_file
from bot.server.render_template import render_page
from bot.config import Telegram

routes = web.RouteTableDef()
db = Database()

@routes.get('/login')
async def login_get(request):
    session = await get_session(request)
    redirect_url = session.get('redirect_url', '/home')
    return web.Response(text=await render_page(None, None, route='login', redirect_url=redirect_url),
                        content_type='text/html')

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
        return web.Response(text=await render_page(None, None, route='login', msg="Invalid credentials"),
                            content_type='text/html')

@routes.get('/home')
async def home_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        channels = await get_chats()
        phtml = await posts_chat(channels)
        playlists = await db.get_Dbfolder('root')
        dhtml = await post_playlist(playlists)
        is_admin = (user == Telegram.ADMIN_USERNAME)

        html = await render_page(None, None, route='home', html=phtml, playlist=dhtml,
                                is_admin=is_admin)
        return web.Response(text=html, content_type='text/html')
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

        query = request.query.get('q', '')
        page = int(request.query.get('page', 1))

        results = await db.search_files(query, page)
        html = await render_page(None, None, route='search', search_results=results, query=query)
        return web.Response(text=html, content_type='text/html')
    except Exception:
        logging.exception("Error in search page")
        return web.Response(text="Internal Server Error", status=500)

@routes.get('/playlist')
async def playlist_page(request):
    try:
        session = await get_session(request)
        user = session.get('user')
        if not user:
            session['redirect_url'] = request.path_qs
            return web.HTTPFound('/login')

        parent = request.query.get('db', 'root')
        page = int(request.query.get('page', 1))

        playlists = await db.get_Dbfolder(parent, page=page)
        files = await db.get_dbFiles(parent, page=page)
        text = await db.get_info(parent)

        dhtml = await post_playlist(playlists)
        dphtml = await posts_db_file(files)
        is_admin = (user == Telegram.ADMIN_USERNAME)

        html = await render_page(parent, None, route='playlist', playlist=dhtml, database=dphtml,
                                msg=text, is_admin=is_admin)

        return web.Response(text=html, content_type='text/html')
    except Exception:
        logging.exception("Error in playlist page")
        return web.Response(text="Internal Server Error", status=500)

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

        html = await render_page(message_id, secure_hash, route='video', encodedname=encodedname)
        return web.Response(text=html, content_type='text/html')
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
        html = await render_page(None, None, route='channels', channels=channels)
        return web.Response(text=html, content_type='text/html')
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

        html = await render_page(None, None, route='settings')
        return web.Response(text=html, content_type='text/html')
    except Exception:
        logging.exception("Settings page error")
        return web.Response(text="Internal server error", status=500)

@routes.get('/{tail:.*}')
async def catch_all_404(request):
    return web.Response(text="404 Not Found", status=404)
