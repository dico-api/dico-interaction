from dico import ApplicationCommand, Snowflake, ApplicationCommandOption

from .exception import InvalidOptionParameter
from .utils import read_function, to_option_type


class InteractionCommand:
    def __init__(self, coro, command: ApplicationCommand, guild_id: Snowflake = None, subcommand: str = None, subcommand_group: str = None):
        self.coro = coro
        self.command = command
        self.guild_id = guild_id
        self.subcommand = subcommand
        self.subcommand_group = subcommand_group

    async def invoke(self, interaction, options: dict):
        param_data = read_function(self.coro)
        required_options = {k: v for k, v in param_data.items() if v["required"]}
        missing_options = [x for x in required_options if x not in options]
        missing_params = [x for x in options if x not in param_data]
        if missing_options or missing_params:
            raise InvalidOptionParameter
        return await self.coro(interaction, **options)

    def get_options(self):
        resp = self.command.options
        param_data = read_function(self.coro)
        if param_data and not resp:
            for k, v in param_data.items():
                try:
                    option = ApplicationCommandOption(option_type=to_option_type(v["annotation"]),
                                                      name=k,
                                                      description="No description.",
                                                      required=v["required"])
                    resp.append(option)
                except NotImplementedError:
                    raise TypeError("unsupported type detected, in this case please manually pass options param to command decorator.") from None
        return resp
