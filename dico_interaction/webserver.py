import asyncio
import typing

import dico
from dico.api import APIClient
from dico.http.async_http import AsyncHTTPRequest

import sanic
from sanic.response import json
from sanic.exceptions import abort

from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

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
        self.loop = loop or asyncio.get_event_loop()
        self.dico_api = APIClient(token, base=AsyncHTTPRequest, loop=self.loop, default_allowed_mentions=allowed_mentions, application_id=application_id)
        self.interaction = interaction
        self.__verify_key = VerifyKey(bytes.fromhex(public_key))
        self.sanic_webserver = sanic.Sanic("dico_interaction")
        self.sanic_webserver.add_route(self.receive_interaction, "/", methods=["POST"])
        self.sanic_webserver.register_middleware(self.verify_security)

    async def receive_interaction(self, request: sanic.Request):
        if request.json["type"] == 1:
            return json({"type": 1})
        interaction = InteractionContext.create(self.dico_api, request.json)
        return json(await self.interaction.receive(interaction))  # This returns initial response.

    async def verify_security(self, request: sanic.Request):
        try:
            sign = request.headers["X-Signature-Ed25519"]
            message = request.headers["X-Signature-Timestamp"].encode() + request.body
            self.__verify_key.verify(message, bytes.fromhex(sign))
        except (BadSignatureError, KeyError):
            return abort(401, "Invalid Signature")

    def run(self, *args, **kwargs):
        self.sanic_webserver.run(*args, **kwargs)

    async def close(self):
        await self.dico_api.http.close()
        self.sanic_webserver.stop()
