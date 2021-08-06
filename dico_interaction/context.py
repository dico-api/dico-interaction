import asyncio

from dico import Interaction, InteractionResponse


class InteractionContext(Interaction):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.respond_via_endpoint = kwargs.get("respond_via_endpoint", True)
        self.response = asyncio.Future()

    def create_response(self, interaction_response: InteractionResponse):
        if not self.respond_via_endpoint:
            self.response.set_result(interaction_response)
        else:
            super().create_response(interaction_response)

    @classmethod
    def from_interaction(cls, interaction: Interaction):
        raise NotImplementedError
