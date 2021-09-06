import typing
from dico import ApplicationCommandTypes, ApplicationCommandOption, ApplicationCommandOptionType, Snowflake, ApplicationCommand
from .command import InteractionCommand
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
            guild_id: typing.Union[int, str, Snowflake] = None):
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
        cmd = InteractionCommand(coro, _command, guild_id, subcommand, subcommand_group)
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
          guild_id: typing.Union[int, str, Snowflake] = None):
    return command(name=name,
                   subcommand=subcommand,
                   subcommand_group=subcommand_group,
                   description=description,
                   subcommand_description=subcommand_description,
                   subcommand_group_description=subcommand_group_description,
                   options=options,
                   default_permission=default_permission,
                   guild_id=guild_id)


def context_menu(name: str = None,
                 menu_type: typing.Union[int, ApplicationCommandTypes] = ApplicationCommandTypes.MESSAGE,
                 guild_id: typing.Union[int, str, Snowflake] = None):
    if int(menu_type) == ApplicationCommandTypes.CHAT_INPUT:
        raise TypeError("unsupported context menu type for context_menu decorator.")
    return command(name=name, description="", command_type=menu_type, guild_id=guild_id)


def component_callback(custom_id: str = None):
    def wrap(coro):
        return ComponentCallback(custom_id, coro)
    return wrap
