import typing
from dico import ApplicationCommand, Snowflake, ApplicationCommandOption

from .context import InteractionContext
from .exception import InvalidOptionParameter, CheckFailed
from .utils import read_function, to_option_type, is_coro


class InteractionCommand:
    def __init__(self,
                 coro,
                 command: ApplicationCommand,
                 guild_id: Snowflake = None,
                 subcommand: str = None,
                 subcommand_group: str = None,
                 checks: typing.Optional[typing.List[typing.Callable[[InteractionContext], typing.Union[bool, typing.Awaitable[bool]]]]] = None,
                 connector: dict = None):
        self.coro = coro
        self.command = command
        self.guild_id = guild_id
        self.subcommand = subcommand
        self.subcommand_group = subcommand_group
        self.checks = checks or []
        self.connector = connector or {}

        if hasattr(self.coro, "_extra_options"):
            self.add_options(*reversed(self.coro._extra_options))
        if hasattr(self.coro, "_checks"):
            self.checks.extend(self.coro._checks)

        opts = self.__command_option
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
        self.__command_option = opts
        self.self_or_cls = None
        self.autocompletes = []

    def register_self_or_cls(self, addon):
        self.self_or_cls = addon

    async def evaluate_checks(self, interaction: InteractionContext):
        if self.self_or_cls and hasattr(self.self_or_cls, "addon_interaction_check") and not await self.self_or_cls.addon_interaction_check(interaction):
            return False
        resp = [n for n in [(await x(interaction)) if is_coro(x) else x(interaction) for x in self.checks] if not n]
        return not resp

    async def invoke(self, interaction, options: dict):
        if not await self.evaluate_checks(interaction):
            raise CheckFailed
        param_data = read_function(self.coro)
        options = {self.connector.get(k, k): v for k, v in options.items()}
        required_options = {k: v for k, v in param_data.items() if v["required"]}
        missing_options = [x for x in required_options if x not in options]
        missing_params = [x for x in options if x not in param_data]
        if missing_options or missing_params:
            raise InvalidOptionParameter
        args = (interaction,) if self.self_or_cls is None else (self.self_or_cls, interaction)
        return await self.coro(*args, **options)

    def add_options(self, *options: ApplicationCommandOption):
        if hasattr(self, "__options_from_args") and self.__options_from_args:
            self.__command_option = []
            self.__options_from_args = False
        self.__command_option.extend(options)

    def autocomplete(self, option: str):
        raise NotImplementedError
        def wrap(coro):
            resp = autocomplete(name=self.command.name, subcommand=self.subcommand, subcommand_group=self.subcommand_group, option=option)(coro)
            self.autocompletes.append(resp)
            return resp
        return wrap

    @property
    def __command_option(self):
        if self.subcommand_group:
            return self.command.options[0].options[0].options
        elif self.subcommand:
            return self.command.options[0].options
        else:
            return self.command.options

    @__command_option.setter
    def __command_option(self, value):
        if self.subcommand_group:
            self.command.options[0].options[0].options = value
        elif self.subcommand:
            self.command.options[0].options = value
        else:
            self.command.options = value


class AutoComplete:
    def __init__(self, coro, name: str, subcommand_group: str, subcommand: str, option: str):
        self.coro = coro
        self.name = name
        self.subcommand_group = subcommand_group
        self.subcommand = subcommand
        self.option = option
        self.self_or_cls = None

    def register_self_or_cls(self, addon):
        self.self_or_cls = addon

    def invoke(self, interaction, options: dict):
        args = (interaction,) if self.self_or_cls is None else (self.self_or_cls, interaction)
        return self.coro(*args)


def autocomplete(*names: str, name: str = None, subcommand_group: str = None, subcommand: str = None, option: str = None):
    if names:
        if not name:
            name = names[0]
        if not option:
            option = names[-1]
        if len(names) == 3 and not subcommand:
            subcommand = names[1]
        elif len(names) == 4:
            if not subcommand_group:
                subcommand_group = names[1]
            if not subcommand:
                subcommand = names[2]

    def wrap(coro):
        return AutoComplete(coro, name, subcommand_group, subcommand, option)
    return wrap
