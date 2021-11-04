import sys
import typing
import asyncio
import logging
import traceback
import copy

from dico import (
    ApplicationCommand,
    ApplicationCommandTypes,
    ApplicationCommandOption,
    ApplicationCommandInteractionDataOption,
    ApplicationCommandOptionType,
    Snowflake,
    Client
)

from .command import InteractionCommand, AutoComplete
from .command import autocomplete as autocomplete_deco
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
    :param guild_id_lock: Guild ID to force-apply to all commands. This is useful for testing commands.

    :ivar loop: asyncio Loop of the client.
    :ivar commands: Dict of commands registered to the client.
    :ivar subcommands: Dict of subcommands registered to the client.
    :ivar subcommand_groups: Dict of subcommand groups registered to the client.
    :ivar components: Dict of component callbacks registered to the client.
    :ivar logger: Logger of the client.
    :ivar respond_via_endpoint: Whether to automatically register commands.
    :ivar guild_id_lock: Guild ID that will be force-applied to all commands.
    """
    def __init__(self,
                 *,
                 loop: asyncio.AbstractEventLoop = None,
                 respond_via_endpoint: bool = True,
                 client: typing.Optional[Client] = None,
                 auto_register_commands: bool = False,
                 guild_id_lock: typing.Optional[Snowflake.TYPING] = None,
                 context_cls: typing.Type[InteractionContext] = InteractionContext):
        self.loop = loop or asyncio.get_event_loop()

        # Storing commands separately is to handle easily.
        self.commands = {}
        self.subcommands = {}
        self.subcommand_groups = {}

        self.components = {}
        self.autocompletes = {}

        self.logger = logging.getLogger("dico.interaction")
        self.respond_via_endpoint = respond_via_endpoint
        self.guild_id_lock = guild_id_lock
        self.context_cls = context_cls
        self.client = client
        if self.client is not None:
            self.client.interaction = self

        if auto_register_commands and not self.client:
            raise ValueError("You must pass dico.Client to use auto_register_commands in InteractionClient.")
        elif auto_register_commands:
            self.loop.create_task(self.register_commands())

        if self.client:
            self.client.on_interaction_create = self.receive

    async def register_commands(self):
        """
        Automatically registers command to discord.
        """
        await self.client.wait_ready()
        self.logger.info("Registering commands...")
        commands = self.export_commands()
        if commands["global"]:
            await self.client.bulk_overwrite_application_commands(*commands["global"])
            self.logger.info(f"Successfully registered global commands.")
        if commands["guild"]:
            for k, v in commands["guild"].items():
                await self.client.bulk_overwrite_application_commands(*v, guild=k)
                self.logger.info(f"Successfully registered guild commands at {k}.")

    async def receive(self, interaction: InteractionContext) -> typing.Optional[dict]:
        """
        Receive and handle interaction.

        .. note::
            If ``respond_via_endpoint`` is set to ``False``, you can get initial response as dict by awaiting.

        :param interaction: Interaction received.
        :type interaction: :class:`.context.InteractionContext`
        :return: Optional[dict]
        """
        if not isinstance(interaction, self.context_cls):
            interaction = self.context_cls.from_interaction(interaction, self.logger)
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
        elif interaction.type.application_command_autocomplete:
            target = self.get_autocomplete(interaction)
        else:
            return

        if not target:
            return

        self.loop.create_task(self.handle_interaction(target, interaction))
        # await self.handle_command(target, interaction)

        if not self.respond_via_endpoint:
            resp = await interaction.response
            return resp.to_dict()

    def get_command(self, interaction: InteractionContext) -> typing.Optional[InteractionCommand]:
        """
        Gets command based on interaction received.

        :param InteractionContext interaction: Interaction received.
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
    def __extract_subcommand_group(options: typing.List[ApplicationCommandInteractionDataOption]):
        if options:
            option = options[0]  # Only one option is passed if it is subcommand group.
            if option.type.sub_command_group:
                return option

    @staticmethod
    def __extract_subcommand(options: typing.List[ApplicationCommandInteractionDataOption]):
        if options:
            option = options[0]  # Only one option is passed if it is subcommand.
            if option.type.sub_command:
                return option

    def get_autocomplete(self, interaction: InteractionContext) -> typing.Optional[AutoComplete]:
        """
        Gets autocomplete based on interaction received.

        :param InteractionContext interaction: Interaction received.
        :return: Optional[AutoComplete]
        """
        subcommand_group = self.__extract_subcommand_group(interaction.data.options)
        subcommand = self.__extract_subcommand(subcommand_group.options if subcommand_group else interaction.data.options)
        option = [x for x in (subcommand_group.options if subcommand_group else subcommand.options if subcommand else interaction.data.options) if x.focused][0]
        if subcommand_group:
            key = f"{interaction.data.name}:{subcommand_group.name}:{subcommand.name}:{option.name}"
        elif subcommand:
            key = f"{interaction.data.name}:{subcommand.name}:{option.name}"
        else:
            key = f"{interaction.data.name}:{option.name}"
        return self.autocompletes.get(key)

    async def handle_interaction(self, target: typing.Union[InteractionCommand, ComponentCallback, AutoComplete], interaction: InteractionContext):
        """
        Handles received interaction.

        :param target: What to execute.
        :type target: Union[InteractionCommand, ComponentCallback, AutoComplete]
        :param InteractionContext interaction: Context to use.
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
            await self.execute_error_handler(target, interaction, ex)

    async def execute_error_handler(self, target: typing.Union[InteractionCommand, ComponentCallback], interaction: InteractionContext, ex: Exception):
        """
        Executes error handler.
        This is intended to be used internally.

        :param target: Target interaction object.
        :param interaction: Interaction context object.
        :param ex: Exception raised.
        """
        if target.self_or_cls:
            if hasattr(target.self_or_cls, "on_addon_interaction_error") and await target.self_or_cls.on_addon_interaction_error(interaction, ex):
                return
            if hasattr(target.self_or_cls, "on_interaction_error") and await target.self_or_cls.on_interaction_error(interaction, ex):
                return
        if hasattr(interaction.client, "dispatch") and interaction.client.events.get("INTERACTION_ERROR"):
            interaction.client.dispatch("interaction_error", interaction, ex)
        else:
            tb = ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))
            title = f"Exception while executing command {interaction.data.name}" if interaction.type.application_command else \
                f"Exception while executing callback of {interaction.data.custom_id}"
            print(f"{title}:\n{tb}", file=sys.stderr)

    def wait_interaction(self, *, timeout: float = None, check: typing.Callable[[InteractionContext], bool] = None):
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

    def export_commands(self) -> dict:
        """
        Exports commands of the client as the form below.

        .. code-block:: python

            {
                "global": [...],
                "guild": {
                    GUILD_ID_1: [...],
                    GUILD_ID_2: [...],
                    ...
                }
            }

        :return: dict
        """
        cmds = {"global": [], "guild": {}}

        for cmd in self.commands.values():
            if cmd.guild_id is not None:
                if cmds["guild"].get(cmd.guild_id) is None:
                    cmds["guild"][cmd.guild_id] = []
                cmds["guild"][cmd.guild_id].append(cmd.command)
            else:
                cmds["global"].append(cmd.command)

        subcommands = {"global": {}, "guild": {}}

        for p_cmd in self.subcommands.values():
            for c_cmd in p_cmd.values():
                if c_cmd.guild_id is not None:
                    subcommands["guild"][c_cmd.guild_id] = {}

        for p_cmd in self.subcommand_groups.values():
            for c_cmd in p_cmd.values():
                for s_cmd in c_cmd.values():
                    if s_cmd.guild_id is not None:
                        subcommands["guild"][s_cmd.guild_id] = {}

        for p_k, p_v in self.subcommands.items():
            for c_k, c_v in p_v.items():
                if c_v.guild_id is not None:
                    data = subcommands["guild"][c_v.guild_id]
                else:
                    data = subcommands["global"]

                if data.get(p_k) is None:
                    data[p_k] = {}
                data[p_k][c_k] = c_v.command

                if c_v.guild_id is not None:
                    subcommands["guild"][c_v.guild_id] = data
                else:
                    subcommands["global"] = data

        for p_k, p_v in self.subcommand_groups.items():
            for c_k, c_v in p_v.items():
                for s_k, s_v in c_v.items():
                    if s_v.guild_id is not None:
                        data = subcommands["guild"][s_v.guild_id]
                    else:
                        data = subcommands["global"]

                    if data.get(p_k) is None:
                        data[p_k] = {}
                    if data[p_k].get(c_k) is None:
                        data[p_k][c_k] = {}
                    data[p_k][c_k][s_k] = s_v.command

                    if s_v.guild_id is not None:
                        subcommands["guild"][s_v.guild_id] = data
                    else:
                        subcommands["global"] = data

        def get_command(data):
            data = data.values()
            base_cmd = None

            for p_cmd in data:
                if isinstance(p_cmd, dict):
                    base_c_cmd = None
                    for c_cmd in p_cmd.values():
                        if base_c_cmd is None:
                            base_c_cmd = c_cmd
                        else:
                            base_c_cmd.options[0].options.append(c_cmd.options[0].options[0])

                    if base_cmd is None:
                        base_cmd = base_c_cmd
                    else:
                        base_cmd.options.append(base_c_cmd.options[0])
                else:
                    if base_cmd is None:
                        base_cmd = p_cmd
                    else:
                        base_cmd.options.append(p_cmd.options[0])
            return base_cmd

        for cmd in subcommands["global"].values():
            cmds["global"].append(get_command(cmd))

        for guild_id, guild_cmds in subcommands["guild"].items():
            if cmds["guild"].get(guild_id) is None:
                cmds["guild"][guild_id] = []
            for cmd in guild_cmds.values():
                cmds["guild"][guild_id].append(get_command(cmd))

        return cmds

    def add_command(self, interaction: InteractionCommand):
        """
        Adds new interaction command to the client.

        :param interaction: Command to add.
        """
        if self.guild_id_lock:
            interaction.guild_id = self.guild_id_lock
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
        """
        Removes command from client.

        :param interaction: Command to remove.
        """
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
        """
        Adds component callback to the client.

        :param callback: Callback to add.
        """
        if callback.custom_id in self.components:
            raise
        self.components[callback.custom_id] = callback

    def remove_callback(self, callback: ComponentCallback):
        """
        Removes callback from client.

        :param callback: Callback to remove.
        """
        if callback.custom_id in self.components:
            del self.components[callback.custom_id]
        else:
            raise

    def add_autocomplete(self, autocomplete: AutoComplete):
        """
        Adds autocomplete to the client.

        :param autocomplete: Autocomplete to add.
        """
        if autocomplete.subcommand_group:
            key = f"{autocomplete.name}:{autocomplete.subcommand_group}:{autocomplete.subcommand}:{autocomplete.option}"
        elif autocomplete.subcommand:
            key = f"{autocomplete.name}:{autocomplete.subcommand}:{autocomplete.option}"
        else:
            key = f"{autocomplete.name}:{autocomplete.name}"
        if key in self.autocompletes:
            raise
        self.autocompletes[key] = autocomplete

    def remove_autocomplete(self, autocomplete: AutoComplete):
        """
        Removes autocomplete from the client.

        :param autocomplete: Autocomplete to remove.
        """
        if autocomplete.subcommand_group:
            key = f"{autocomplete.name}:{autocomplete.subcommand_group}:{autocomplete.subcommand}:{autocomplete.option}"
        elif autocomplete.subcommand:
            key = f"{autocomplete.name}:{autocomplete.subcommand}:{autocomplete.option}"
        else:
            key = f"{autocomplete.name}:{autocomplete.name}"
        if key not in self.autocompletes:
            raise
        del self.autocompletes[key]

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
                guild_id: typing.Union[int, str, Snowflake] = None,
                connector: typing.Dict[str, str] = None):
        """
        Creates and registers interaction command to the client.

        .. note::
            You should use :meth:`.slash` or :meth:`.context_menu`.

        .. warning::
            It is not recommended to create subcommand using options, since it won't be handled properly in the client.

        :param name: Name of the command.
        :param subcommand: Subcommand of the command.
        :param subcommand_group: Subcommand group of the command.
        :param description: Description of the command.
        :param subcommand_description: Description of subcommand.
        :param subcommand_group_description: Description of subcommand group.
        :param command_type: Type of command.
        :param options: Options of the command.
        :param default_permission: Whether default permission is enabled.
        :param guild_id: ID of the guild.
        :param connector: Option parameter connector.
        """
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
                               guild_id=guild_id,
                               connector=connector)(coro)
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
              guild_id: typing.Union[int, str, Snowflake] = None,
              connector: typing.Dict[str, str] = None):
        """
        Creates and registers slash command to the client.

        Example:
        .. code-block:: python

            @interaction.slash("example")
            async def example_slash(ctx):
                ...

        Connector Example:
        .. code-block:: python

            {
                "옵션": "option",
                "시간": "hour"
            }

        .. warning::
            It is not recommended to create subcommand using options, since it won't be handled properly in the client.

        :param name: Name of the command.
        :param subcommand: Subcommand of the command.
        :param subcommand_group: Subcommand group of the command.
        :param description: Description of the command.
        :param subcommand_description: Description of subcommand.
        :param subcommand_group_description: Description of subcommand group.
        :param options: Options of the command.
        :param default_permission: Whether default permission is enabled.
        :param guild_id: ID of the guild.
        :param connector: Option parameter connector.
        """
        return self.command(name=name,
                            subcommand=subcommand,
                            subcommand_group=subcommand_group,
                            description=description,
                            subcommand_description=subcommand_description,
                            subcommand_group_description=subcommand_group_description,
                            options=options,
                            default_permission=default_permission,
                            guild_id=guild_id,
                            connector=connector)

    def context_menu(self,
                     name: str = None,
                     menu_type: typing.Union[int, ApplicationCommandTypes] = ApplicationCommandTypes.MESSAGE,
                     guild_id: typing.Union[int, str, Snowflake] = None):
        """
        Creates and registers context menu to the client.

        :param name: Name of the command.
        :param menu_type: Type of the context menu.
        :param guild_id: ID of the guild.
        """
        if int(menu_type) == ApplicationCommandTypes.CHAT_INPUT:
            raise TypeError("unsupported context menu type for context_menu decorator.")
        return self.command(name=name, description="", command_type=menu_type, guild_id=guild_id)

    def component_callback(self, custom_id: str = None):
        """
        Adds component callback to the client.

        :param custom_id: Custom ID of the component. Can be prefix of the custom ID.
        """
        def wrap(coro):
            callback = ComponentCallback(custom_id, coro)
            self.add_callback(callback)
            return callback
        return wrap

    def autocomplete(self, *names: str, name: str = None, subcommand_group: str = None, subcommand: str = None, option: str = None):
        """
        Adds autocomplete to the client. Supports two style:

        .. code-block: python

            @interaction.autocomplete("example", "option")
            async def ...(ctx: InteractionContext):
                await ctx.send(choices=[...])

            @interaction.autocomplete(name="example", option="option")
            async def ...(ctx: InteractionContext):
                await ctx.send(choices=[...])

        :param name: Name of the command that has autocomplete option.
        :param subcommand_group: Subcommand group of the command.
        :param subcommand: Subcommand of the command.
        :param option: Name of the option with autocomplete enabled.
        """
        def wrap(coro):
            autocomplete = autocomplete_deco(*names, name=name, subcommand_group=subcommand_group, subcommand=subcommand, option=option)(coro)
            self.add_autocomplete(autocomplete)
            return autocomplete
        return wrap
