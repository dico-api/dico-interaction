class ComponentCallback:
    # This is kinda temporary

    def __init__(self, coro):
        self.coro = coro

    def invoke(self, interaction, *_, **__):
        return self.coro(interaction)
