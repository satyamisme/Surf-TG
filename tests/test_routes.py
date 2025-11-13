import unittest
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web
from bot.server.stream_routes import routes
from unittest.mock import MagicMock

class MyAppTestCase(AioHTTPTestCase):

    async def get_application(self):
        app = web.Application()
        from aiohttp_session import setup
        from aiohttp_session.cookie_storage import EncryptedCookieStorage
        from cryptography.fernet import Fernet
        secret_key = Fernet.generate_key()
        setup(app, EncryptedCookieStorage(Fernet(secret_key)))
        import aiohttp_jinja2
        import jinja2
        aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('bot/server/template'))
        app.add_routes(routes)
        app['db'] = MagicMock()
        return app

    @unittest_run_loop
    async def test_login_page_loads(self):
        resp = await self.client.request("GET", "/login")
        assert resp.status == 200
        text = await resp.text()
        assert "Login" in text

    @unittest_run_loop
    async def test_home_page_redirects_when_not_logged_in(self):
        resp = await self.client.request("GET", "/")
        assert resp.status == 200
        assert resp.url.path == '/login'

if __name__ == '__main__':
    unittest.main()
