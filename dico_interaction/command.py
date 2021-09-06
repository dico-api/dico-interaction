import typing
from dico import ApplicationCommand, Snowflake, ApplicationCommandOption, ApplicationCommandOptionType, ApplicationCommandOptionChoice

from .exception import InvalidOptionParameter
from .utils import read_function, to_option_type


class InteractionCommand:
    def __init__(self, coro, command: ApplicationCommand, guild_id: Snowflake = None, subcommand: str = None, subcommand_group: str = None):
        self.coro = coro
        self.command = command
        self.guild_id = guild_id
        self.subcommand = subcommand
        self.subcommand_group = subcommand_group

        if hasattr(self.coro, "_extra_options"):
            self.add_options(*self.coro._extra_options)

        opts = self.command.options
        param_data = read_function(self.coro)
        self.__options_from_args = param_data and not opts
        if self.__options_from_args:
            for k, v in param_data.items():
                try:
                    opt = ApplicationCommandOption(option_type=to_option_type(v["annotation"]),
                                                   name=k,
                                                   description="No description.",
                                                   required=v["required"])
                    opts.append(opt)
                except NotImplementedError:
                    raise TypeError("unsupported type detected, in this case please manually pass options param to command decorator.") from None
        self.command.options = opts
        self.self_or_cls = None

    def register_self_or_cls(self, addon):
        self.self_or_cls = addon

    async def invoke(self, interaction, options: dict):
        param_data = read_function(self.coro)
        required_options = {k: v for k, v in param_data.items() if v["required"]}
        missing_options = [x for x in required_options if x not in options]
        missing_params = [x for x in options if x not in param_data]
        if missing_options or missing_params:
            raise InvalidOptionParameter
        args = (interaction,) if self.self_or_cls is None else (self.self_or_cls, interaction)
        return await self.coro(*args, **options)

    def add_options(self, *options: ApplicationCommandOption):
        if hasattr(self, "__options_from_args") and self.__options_from_args:
            self.command.options = []
            self.__options_from_args = False
        self.command.options.extend(options)


def option(option_type: typing.Union[ApplicationCommandOptionType, int],
           *,
           name: str,
           description: str,
           required: bool = False,
           choices: typing.List[ApplicationCommandOptionChoice] = None,
           options: typing.List[ApplicationCommandOption] = None):
    if int(option_type) == ApplicationCommandOptionType.SUB_COMMAND_GROUP and choices:
        raise TypeError("choices is not allowed if option type is SUB_COMMAND_GROUP.")
    if int(option_type) == ApplicationCommandOptionType.SUB_COMMAND_GROUP and not options:
        raise TypeError("you must pass options if option type is SUB_COMMAND_GROUP.")
    option_to_add = ApplicationCommandOption(option_type=option_type, name=name, description=description, required=required, choices=choices, options=options)

    def wrap(maybe_cmd):
        if isinstance(maybe_cmd, InteractionCommand):
            maybe_cmd.add_options(option_to_add)
        else:
            if not hasattr(maybe_cmd, "_extra_options"):
                maybe_cmd._extra_options = []
            maybe_cmd._extra_options.append(option_to_add)
        return maybe_cmd

    return wrap
