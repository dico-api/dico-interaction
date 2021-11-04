import typing
from dico import (
    ApplicationCommandTypes, ApplicationCommandOption, ApplicationCommandOptionType, Snowflake, ApplicationCommand, ApplicationCommandOptionChoice, ChannelTypes
)
from .command import InteractionCommand
from .context import InteractionContext
from .component import ComponentCallback


def command(name: str = None,
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
    if int(command_type) == ApplicationCommandTypes.CHAT_INPUT and not description:
        raise ValueError("description must be passed if type is CHAT_INPUT.")
    description = description or ""
    options = options or []
    if subcommand:
        if int(command_type) != ApplicationCommandTypes.CHAT_INPUT:
            raise TypeError("subcommand is exclusive to CHAT_INPUT.")
        if not subcommand_description:
            raise ValueError("subcommand_description must be passed if subcommand is set.")
        options = [ApplicationCommandOption(option_type=ApplicationCommandOptionType.SUB_COMMAND,
                                            name=subcommand,
                                            description=subcommand_description,
                                            options=options.copy())]
    if subcommand_group:
        if int(command_type) != ApplicationCommandTypes.CHAT_INPUT:
            raise TypeError("subcommand_group is exclusive to CHAT_INPUT.")
        if not subcommand:
            raise ValueError("subcommand must be passed if subcommand_group is set.")
        if not subcommand_group_description:
            raise ValueError("subcommand_group_description must be passed if subcommand_group is set.")
        options = options.copy()
        options = [ApplicationCommandOption(option_type=ApplicationCommandOptionType.SUB_COMMAND_GROUP,
                                            name=subcommand_group,
                                            description=subcommand_group_description,
                                            options=options.copy())]

    def wrap(coro):
        _command = ApplicationCommand(name or coro.__name__, description, command_type, options, default_permission)
        cmd = InteractionCommand(coro, _command, guild_id, subcommand, subcommand_group, connector=connector)
        return cmd

    return wrap


def slash(name: str = None,
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
    return command(name=name,
                   subcommand=subcommand,
                   subcommand_group=subcommand_group,
                   description=description,
                   subcommand_description=subcommand_description,
                   subcommand_group_description=subcommand_group_description,
                   options=options,
                   default_permission=default_permission,
                   guild_id=guild_id,
                   connector=connector)


def context_menu(name: str = None,
                 menu_type: typing.Union[int, ApplicationCommandTypes] = ApplicationCommandTypes.MESSAGE,
                 guild_id: typing.Union[int, str, Snowflake] = None):
    if int(menu_type) == ApplicationCommandTypes.CHAT_INPUT:
        raise TypeError("unsupported context menu type for context_menu decorator.")
    return command(name=name, description="", command_type=menu_type, guild_id=guild_id)


def option(option_type: typing.Union[ApplicationCommandOptionType, int],
           *,
           name: str,
           description: str,
           required: typing.Optional[bool] = None,
           choices: typing.Optional[typing.List[ApplicationCommandOptionChoice]] = None,
           autocomplete: typing.Optional[bool] = None,
           options: typing.Optional[typing.List[ApplicationCommandOption]] = None,
           channel_types: typing.Optional[typing.List[typing.Union[int, ChannelTypes]]] = None,):
    if int(option_type) == ApplicationCommandOptionType.SUB_COMMAND_GROUP and choices:
        raise TypeError("choices is not allowed if option type is SUB_COMMAND_GROUP.")
    if int(option_type) == ApplicationCommandOptionType.SUB_COMMAND_GROUP and not options:
        raise TypeError("you must pass options if option type is SUB_COMMAND_GROUP.")
    option_to_add = ApplicationCommandOption(option_type=option_type,
                                             name=name,
                                             description=description,
                                             required=required,
                                             choices=choices,
                                             autocomplete=autocomplete,
                                             options=options,
                                             channel_types=channel_types)

    def wrap(maybe_cmd):
        if isinstance(maybe_cmd, InteractionCommand):
            maybe_cmd.add_options(option_to_add)
        else:
            if not hasattr(maybe_cmd, "_extra_options"):
                maybe_cmd._extra_options = []
            maybe_cmd._extra_options.append(option_to_add)
        return maybe_cmd

    return wrap


def checks(*funcs: typing.Callable[[InteractionContext], typing.Union[bool, typing.Awaitable[bool]]]):
    def wrap(maybe_cmd):
        if isinstance(maybe_cmd, InteractionCommand):
            maybe_cmd.checks.extend(funcs)
        else:
            if hasattr(maybe_cmd, "_checks"):
                maybe_cmd._checks.extend(funcs)
            else:
                maybe_cmd._checks = [*funcs]
        return maybe_cmd
    return wrap


def component_callback(custom_id: str = None):
    def wrap(coro):
        return ComponentCallback(custom_id, coro)
    return wrap
