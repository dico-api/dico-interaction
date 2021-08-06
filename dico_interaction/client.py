import typing
import asyncio
import logging

from dico import Interaction, ApplicationCommand, ApplicationCommandOption

from .command import SlashCommand
from .context import InteractionContext


class InteractionClient:
    def __init__(self, loop: asyncio.AbstractEventLoop = None, respond_via_endpoint: bool = True):
        self.loop = loop or asyncio.get_event_loop()
        self.commands = {}
        self.components = {}
        self.logger = logging.Logger("dico.interaction")
        self.respond_via_endpoint = respond_via_endpoint

    async def receive(self, interaction: Interaction):
        if not isinstance(interaction, InteractionContext):
            interaction = InteractionContext.from_interaction(interaction)
        if interaction.type.application_command:
            invoke = self.commands.get(interaction.data.name)
        elif interaction.type.message_component:
            invoke = self.components.get(interaction.data.name)
        else:
            return

        if not invoke:
            return

        self.loop.create_task(invoke.invoke(interaction))

        if not self.respond_via_endpoint:
            resp = await interaction.response
            return resp.to_dict()

    def slash(self,
              name: str,
              description: str,
              options: typing.List[ApplicationCommandOption] = None,
              default_permission: bool = True):
        def wrap(coro):
            command = ApplicationCommand(name, description, options, default_permission)
            slash = SlashCommand(coro, command)
            self.commands["name"] = slash
            return slash
        return wrap
