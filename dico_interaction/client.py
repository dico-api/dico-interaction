import sys
import typing
import asyncio
import logging
import traceback

from dico import ApplicationCommand, ApplicationCommandTypes, ApplicationCommandOption, ApplicationCommandOptionType, Snowflake, Client

from .command import InteractionCommand
from .deco import command as command_deco
from .component import ComponentCallback
from .context import InteractionContext


class InteractionClient:
    """
    This handles all interaction.

    .. note::
        - ``auto_register_commands`` must be enabled to properly respond via webserver.
        - Attribute ``interaction`` will be automatically added to your websocket client if you pass param ``client``.

    :param loop: Asyncio loop instance to use in this client. Default ``asyncio.get_event_loop()``.
    :param respond_via_endpoint: Whether to respond via endpoint, which is for gateway response. Otherwise, set to ``False``. Default ``True``.
    :param client: Optional dico client. Passing this enables automatic command register, wait_interaction, and auto event registration.
    :param auto_register_commands: Whether to automatically register commands. Default ``False``.

    :ivar loop: asyncio Loop of the client.
    :ivar commands: Dict of commands registered to the client.
    :ivar subcommands: Dict of subcommands registered to the client.
    :ivar subcommand_groups: Dict of subcommand groups registered to the client.
    :ivar components: Dict of component callbacks registered to the client.
    :ivar logger: Logger of the client.
    :ivar respond_via_endpoint: Whether to automatically register commands.
    """
    def __init__(self,
                 *,
                 loop: asyncio.AbstractEventLoop = None,
                 respond_via_endpoint: bool = True,
                 client: typing.Optional[Client] = None,
                 auto_register_commands: bool = False):
        self.loop = loop or asyncio.get_event_loop()

        # Storing commands separately is to handle easily.
        self.commands = {}
        self.subcommands = {}
        self.subcommand_groups = {}

        self.components = {}
        self.logger = logging.Logger("dico.interaction")
        self.respond_via_endpoint = respond_via_endpoint
        self.client = client
        if self.client is not None:
            self.client.interaction = self

        if auto_register_commands:
            raise NotImplementedError("I gave up, sorry.")

        if auto_register_commands and not self.client:
            raise ValueError("You must pass dico.Client to use auto_overwrite_commands in InteractionClient.")
        elif auto_register_commands:
            self.loop.create_task(self.register_commands())

        if self.client:
            self.client.on_interaction_create = self.receive

    async def register_commands(self):
        """
        Automatically registers command to discord.
        """
        await self.client.wait_ready()
        commands = self.export_commands()
        if commands["global"]:
            await self.client.bulk_overwrite_application_commands(*commands["global"])
        if commands["guild"]:
            for k, v in commands["guild"].items():
                await self.client.bulk_overwrite_application_commands(*v, guild=k)

    async def receive(self, interaction: InteractionContext) -> typing.Optional[dict]:
        """
        Receive and handle interaction.

        .. note::
            If ``respond_via_endpoint`` is set to ``False``, you can get initial response as dict by awaiting.

        :param interaction: Interaction received.
        :type interaction: :class:`.context.InteractionContext`
        :return: Optional[dict]
        """
        print(interaction)
        if not isinstance(interaction, InteractionContext):
            interaction = InteractionContext.from_interaction(interaction, self.logger)
        if self.client:
            self.client.dispatch("interaction", interaction)
        if interaction.type.application_command:
            target = self.get_command(interaction)
        elif interaction.type.message_component:
            target = self.components.get(interaction.data.custom_id)
            if not target:
                maybe = [x for x in self.components if interaction.data.custom_id.startswith(x)]
                if maybe:
                    target = self.components.get(maybe[0])
        else:
            return

        if not target:
            return

        self.loop.create_task(self.handle_command(target, interaction))
        # await self.handle_command(target, interaction)

        if not self.respond_via_endpoint:
            resp = await interaction.response
            return resp.to_dict()

    def get_command(self, interaction: InteractionContext) -> typing.Optional[InteractionCommand]:
        """
        Gets command based on interaction received.

        :param interaction: Interaction received.
        :type interaction: :class:`.context.InteractionContext`
        :return: Optional[InteractionCommand]
        """
        subcommand_group = self.__extract_subcommand_group(interaction.data.options)
        subcommand = self.__extract_subcommand(subcommand_group.options if subcommand_group else interaction.data.options)
        if subcommand_group:
            return self.subcommand_groups.get(interaction.data.name, {}).get(subcommand_group.name, {}).get(subcommand.name)
        elif subcommand:
            return self.subcommands.get(interaction.data.name, {}).get(subcommand.name)
        else:
            return self.commands.get(interaction.data.name)

    @staticmethod
    def __extract_subcommand_group(options: typing.List[ApplicationCommandOption]):
        if options:
            option = options[0]  # Only one option is passed if it is subcommand group.
            if option.type.sub_command_group:
                return option

    @staticmethod
    def __extract_subcommand(options: typing.List[ApplicationCommandOption]):
        if options:
            option = options[0]  # Only one option is passed if it is subcommand.
            if option.type.sub_command:
                return option

    async def handle_command(self, target: typing.Union[InteractionCommand, ComponentCallback], interaction: InteractionContext):
        """
        Handles command or callback.

        :param target: What to execute.
        :type target: Union[:class:`.command.InteractionCommand`, :class:`.component.ComponentCallback`]
        :param interaction: Context to use.
        :type interaction: :class:`.context.InteractionContext`
        """
        subcommand_group = self.__extract_subcommand_group(interaction.data.options)
        subcommand = self.__extract_subcommand(subcommand_group.options if subcommand_group else interaction.data.options)
        options = {}
        opts = subcommand.options if subcommand else interaction.data.options
        for x in opts or []:
            value = x.value
            resolved_types = [ApplicationCommandOptionType.USER,
                              ApplicationCommandOptionType.CHANNEL,
                              ApplicationCommandOptionType.ROLE,
                              ApplicationCommandOptionType.MENTIONABLE]
            if value and int(x.type) in resolved_types:
                if interaction.data.resolved:
                    value = interaction.data.resolved.get(value)
                elif interaction.client.has_cache:
                    value = interaction.client.get(value) or value
            options[x.name] = value
        try:
            await target.invoke(interaction, options)
        except Exception as ex:
            if hasattr(interaction.client, "dispatch") and interaction.client.events.get("interaction_error"):
                interaction.client.dispatch("interaction_error", interaction, ex)
            else:
                tb = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
                title = f"Exception while executing command {interaction.data.name}" if interaction.type.application_command else \
                    f"Exception while executing callback of {interaction.data.custom_id}"
                print(f"{title}:\n{tb}", file=sys.stderr)

    def wait_interaction(self, *, timeout: float = None, check: typing.Callable[[InteractionContext], bool] = None) -> InteractionContext:
        """
        Waits for interaction. Basically same as ``dico.Client.wait`` but with ``interaction`` event as default.

        :param timeout: When to timeout. Default ``None``, which will wait forever.
        :param check: Check to apply.
        :return: :class:`.context.InteractionContext`
        :raises asyncio.TimeoutError: Timed out.
        """
        if not self.client:
            raise AttributeError("you cannot use wait_interaction if you didn't pass client to parameter.")
        return self.client.wait("interaction", timeout=timeout, check=check)

    def export_commands(self):
        raise NotImplementedError("I gave up.")

        global_body = []  # noqa
        pre_global_body = {}
        guild_body = {}
        pre_guild_body = {}

        # extracted_

        for k, v in pre_guild_body.items():
            guild_body[k] = [*v.values()]
        return {"global": [*pre_global_body.values()], "guild": guild_body}

    def add_command(self, interaction: InteractionCommand):
        subcommand_group = interaction.subcommand_group
        subcommand = interaction.subcommand
        name = interaction.command.name
        if subcommand_group:
            if name not in self.subcommand_groups:
                self.subcommand_groups[name] = {}
            if subcommand_group not in self.subcommand_groups[name]:
                self.subcommand_groups[name][subcommand_group] = {}
            if subcommand in self.subcommand_groups[name][subcommand_group]:
                raise
            self.subcommand_groups[name][subcommand_group][subcommand] = interaction
        elif subcommand:
            if name not in self.subcommands:
                self.subcommands[name] = {}
            if subcommand in self.subcommands[name]:
                raise
            self.subcommands[name][subcommand] = interaction
        else:
            if name in self.commands:
                raise
            self.commands[name] = interaction

    def remove_command(self, interaction: InteractionCommand):
        subcommand_group = interaction.subcommand_group
        subcommand = interaction.subcommand
        name = interaction.command.name
        if subcommand_group:
            if name in self.subcommand_groups and subcommand_group in self.subcommand_groups[name] and \
                    subcommand in self.subcommand_groups[name][subcommand_group]:
                del self.subcommand_groups[name][subcommand_group][subcommand]
            else:
                raise
        elif subcommand:
            if name in self.subcommands and subcommand in self.subcommands[name]:
                del self.subcommands[name][subcommand]
            else:
                raise
        else:
            if name in self.commands:
                del self.commands[name]
            else:
                raise

    def add_callback(self, callback: ComponentCallback):
        self.components[callback.custom_id] = callback

    def remove_callback(self, callback: ComponentCallback):
        if callback.custom_id in self.components:
            del self.components[callback.custom_id]
        else:
            raise

    def command(self,
                name: str = None,
                *,
                subcommand: str = None,
                subcommand_group: str = None,
                description: str = None,
                subcommand_description: str = None,
                subcommand_group_description: str = None,
                command_type: typing.Union[int, ApplicationCommandTypes] = ApplicationCommandTypes.CHAT_INPUT,
                options: typing.List[ApplicationCommandOption] = None,
                default_permission: bool = True,
                guild_id: typing.Union[int, str, Snowflake] = None):
        def wrap(coro):
            cmd = command_deco(name,
                               subcommand=subcommand,
                               subcommand_group=subcommand_group,
                               description=description,
                               subcommand_description=subcommand_description,
                               subcommand_group_description=subcommand_group_description,
                               command_type=command_type,
                               options=options,
                               default_permission=default_permission,
                               guild_id=guild_id)(coro)
            self.add_command(cmd)
            return cmd
        return wrap

    def slash(self,
              name: str = None,
              *,
              subcommand: str = None,
              subcommand_group: str = None,
              description: str,
              subcommand_description: str = None,
              subcommand_group_description: str = None,
              options: typing.List[ApplicationCommandOption] = None,
              default_permission: bool = True,
              guild_id: typing.Union[int, str, Snowflake] = None):
        return self.command(name=name,
                            subcommand=subcommand,
                            subcommand_group=subcommand_group,
                            description=description,
                            subcommand_description=subcommand_description,
                            subcommand_group_description=subcommand_group_description,
                            options=options,
                            default_permission=default_permission,
                            guild_id=guild_id)

    def context_menu(self,
                     name: str = None,
                     menu_type: typing.Union[int, ApplicationCommandTypes] = ApplicationCommandTypes.MESSAGE,
                     guild_id: typing.Union[int, str, Snowflake] = None):
        if int(menu_type) == ApplicationCommandTypes.CHAT_INPUT:
            raise TypeError("unsupported context menu type for context_menu decorator.")
        return self.command(name=name, description="", command_type=menu_type, guild_id=guild_id)

    def component_callback(self, custom_id: str = None):
        def wrap(coro):
            callback = ComponentCallback(custom_id, coro)
            self.add_callback(callback)
            return callback
        return wrap
