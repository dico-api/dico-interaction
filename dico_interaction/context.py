import io
import typing
import asyncio
import pathlib

from dico import Interaction, InteractionResponse, InteractionCallbackType, InteractionApplicationCommandCallbackData, Embed, AllowedMentions, Component


class InteractionContext(Interaction):
    def __init__(self, client, resp):
        super().__init__(client, resp)
        self.respond_via_endpoint = resp.get("respond_via_endpoint", True)
        self.response = asyncio.Future()
        self.deferred = False
        self.logger = resp["logger"]

    def defer(self, ephemeral: bool = False, update_message: bool = False):
        if self.type.application_command:
            if update_message:
                self.logger.warning("update_message is only for message component. Ignoring update_message param.")
            callback_type = InteractionCallbackType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
        elif self.type.message_component:
            callback_type = InteractionCallbackType.DEFERRED_UPDATE_MESSAGE if update_message else InteractionCallbackType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
        else:
            raise NotImplementedError
        resp = InteractionResponse(callback_type, InteractionApplicationCommandCallbackData(flags=64 if ephemeral else None))
        self.deferred = True
        return self.create_response(resp)

    def send(self,
             content: str = None,
             *,
             username: str = None,
             avatar_url: str = None,
             tts: bool = False,
             file: typing.Union[io.FileIO, pathlib.Path, str] = None,
             files: typing.List[typing.Union[io.FileIO, pathlib.Path, str]] = None,
             embed: typing.Union[Embed, dict] = None,
             embeds: typing.List[typing.Union[Embed, dict]] = None,
             allowed_mentions: typing.Union[AllowedMentions, dict] = None,
             components: typing.List[typing.Union[dict, Component]]= None,
             ephemeral: bool = False,
             update_message: bool = False):
        if self.type.application_command:
            if update_message:
                self.logger.warning("update_message is only for message component. Ignoring update_message param.")
        if not self.deferred:
            if embed and embeds:
                raise TypeError("you can't pass both embed and embeds.")
            if embed:
                embeds = [embed]
            if file or files:
                self.logger.warning("file and files are not supported on initial response. Ignoring file or files param.")
            callback_type = InteractionCallbackType.UPDATE_MESSAGE if update_message else InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE
            data = InteractionApplicationCommandCallbackData(tts=tts,
                                                             content=content,
                                                             embeds=embeds,
                                                             allowed_mentions=allowed_mentions,
                                                             flags=64 if ephemeral else None,
                                                             components=components)
            resp = InteractionResponse(callback_type, data)
            self.deferred = True
            return self.create_response(resp)
        params = {"content": content,
                  "username": username,
                  "avatar_url": avatar_url,
                  "tts": tts,
                  "file": file,
                  "files": files,
                  "embed": embed,
                  "embeds": embeds,
                  "allowed_mentions": allowed_mentions,
                  "components": components,
                  "ephemeral": ephemeral}
        return self.create_followup_message(**params)

    async def create_response(self, interaction_response: InteractionResponse):
        if not self.respond_via_endpoint:
            self.response.set_result(interaction_response)
        else:
            return await super().create_response(interaction_response)

    @classmethod
    def from_interaction(cls, interaction: Interaction, logger):
        resp = interaction.raw
        resp["logger"] = logger
        return cls(interaction.client, resp)
