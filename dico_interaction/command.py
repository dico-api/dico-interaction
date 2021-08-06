from dico import ApplicationCommand


class SlashCommand:
    def __init__(self, coro, command: ApplicationCommand):
        self.coro = coro
        self.command = command

    def invoke(self):
        return self.coro
