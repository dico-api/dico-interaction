# dico-interaction
Interaction module for dico.

## Features
- Webserver included, powered by Sanic.

## Example

### Webserver
```py
from dico import InteractionResponse, InteractionCallbackType, InteractionApplicationCommandCallbackData
from dico_interaction import InteractionClient, InteractionWebserver, InteractionContext

bot_token = ""
bot_public_key = ""

interaction = InteractionClient(respond_via_endpoint=False)
server = InteractionWebserver(bot_token, bot_public_key, interaction)

@interaction.slash(name="hello", description="Say hello.")
async def hello(ctx: InteractionContext):
    data = InteractionApplicationCommandCallbackData(content="Hello, World!")
    resp = InteractionResponse(InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE,
                               data)
    await ctx.create_response(resp)

server.run(host='0.0.0.0', port=1337)

```
