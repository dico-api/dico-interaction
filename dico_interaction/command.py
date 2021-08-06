from dico import ApplicationCommand


class SlashCommand:
    def __init__(self, coro, command: ApplicationCommand):
        self.coro = coro
        self.command = command

    async def invoke(self, interaction, *args, **kwargs):
        return await self.coro(interaction, *args, **kwargs)
