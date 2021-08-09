# dico-interaction
Interaction module for dico.

## Features
- Webserver included, powered by aiohttp.

## Example

## Gateway Client

```py
from dico import Client
from dico_interaction import InteractionClient, InteractionContext

client = Client("BOT_TOKEN")
interaction = InteractionClient()
client.on_interaction_create = interaction.receive


@interaction.slash(name="hello", description="Say hello.")
async def test_slash(ctx: InteractionContext):
    await ctx.send("Hello, World!")

client.run()

```

### Webserver
```py
import ssl  # SSL is forced to register your webserver URL to discord.
from dico_interaction import InteractionClient, InteractionWebserver, InteractionContext

bot_token = ""
bot_public_key = ""

interaction = InteractionClient(respond_via_endpoint=False)
server = InteractionWebserver(bot_token, bot_public_key, interaction)

@interaction.slash(name="hello", description="Say hello.")
async def hello(ctx: InteractionContext):
    await ctx.send("Hello, World!")

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("cert.pem", "privkey.pem")
server.run(host='0.0.0.0', port=1337, ssl_context=ssl_context)

```
