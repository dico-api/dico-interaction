class ComponentCallback:
    # This is kinda temporary

    def __init__(self, custom_id, coro):
        self.custom_id = custom_id or coro.__name__
        self.coro = coro
        self.self_or_cls = None

    def register_self_or_cls(self, addon):
        self.self_or_cls = addon

    def invoke(self, interaction, *_, **__):
        args = (interaction,) if self.self_or_cls is None else (self.self_or_cls, interaction)
        return self.coro(*args)
