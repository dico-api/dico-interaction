import asyncio
import typing

from aiohttp import web

import dico
from dico.api import APIClient
from dico.http.async_http import AsyncHTTPRequest

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
except ImportError:
    import sys
    print("PyNaCl not installed, webserver won't be available.", file=sys.stderr)
    VerifyKey = lambda _: _
    BadSignatureError = Exception

from .client import InteractionClient
from .context import InteractionContext


class InteractionWebserver:
    def __init__(self,
                 token: str,
                 public_key: str,
                 interaction: InteractionClient,
                 loop: asyncio.AbstractEventLoop = None,
                 allowed_mentions: dico.AllowedMentions = None,
                 application_id: typing.Union[int, str, dico.Snowflake] = None):
        self.loop = loop or interaction.loop or asyncio.get_event_loop()
        self.dico_api = APIClient(token, base=AsyncHTTPRequest, loop=self.loop, default_allowed_mentions=allowed_mentions, application_id=application_id)
        self.interaction = interaction
        self.__verify_key = VerifyKey(bytes.fromhex(public_key))
        self.webserver = web.Application(loop=self.loop, middlewares=[self.verify_security])
        self.webserver.router.add_post("/", self.receive_interaction)

    async def receive_interaction(self, request: web.Request):
        body = await request.json()
        if body["type"] == 1:
            return web.json_response({"type": 1})
        payload = body
        payload["respond_via_endpoint"] = False
        payload["logger"] = self.interaction.logger
        interaction = InteractionContext.create(self.dico_api, payload)
        return web.json_response(await self.interaction.receive(interaction))  # This returns initial response.

    @web.middleware
    async def verify_security(self, request: web.Request, handler):
        if request.method != "POST":
            return await handler(request)
        try:
            sign = request.headers["X-Signature-Ed25519"]
            message = request.headers["X-Signature-Timestamp"].encode() + await request.read()
            self.__verify_key.verify(message, bytes.fromhex(sign))
            return await handler(request)
        except (BadSignatureError, KeyError):
            return web.Response(text="Invalid Signature", status=401)

    async def start(self, host, port, ssl_context):
        self.runner = web.AppRunner(self.webserver)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host, port, ssl_context=ssl_context)
        await site.start()

    async def close(self):
        await self.dico_api.http.close()
        await self.runner.cleanup()

    def run(self, *args, **kwargs):
        try:
            self.loop.create_task(self.start(*args, **kwargs))
            self.loop.run_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.loop.run_until_complete(self.close())
