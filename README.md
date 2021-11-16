# dico-interaction
Interaction module for dico.

## Features
- Webserver included, powered by aiohttp.
- Easier interaction usage.

## Installation
```
pip install -U dico-interaction
```

## Example

### Gateway Client

```py
from dico import Client, Button, ActionRow, ButtonStyles
from dico_interaction import InteractionClient, InteractionContext

client = Client("BOT_TOKEN")
interaction = InteractionClient(client=client)


@interaction.slash(name="hello", description="Say hello.")
async def hello(ctx: InteractionContext):
    button = Button(style=ButtonStyles.PRIMARY, label="Hello!", custom_id=f"hello{ctx.id}")
    await ctx.send("Hello, World!", components=[ActionRow(button)])
    
    
@interaction.context_menu(name="say", menu_type=3)
async def say_menu(ctx: InteractionContext):
    await ctx.send(f"You said: {ctx.target.content}")
    

@interaction.component_callback("hello")
async def hello_callback(ctx: InteractionContext):
    await ctx.send("Hello again!", ephemeral=True)

client.run()

```

### Webserver
```py
import ssl  # SSL is forced to register your webserver URL to discord.
from dico import Button, ActionRow, ButtonStyles
from dico_interaction import InteractionClient, InteractionWebserver, InteractionContext

bot_token = ""
bot_public_key = ""

interaction = InteractionClient(respond_via_endpoint=False)
server = InteractionWebserver(bot_token, bot_public_key, interaction)


@interaction.slash(name="hello", description="Say hello.")
async def hello(ctx: InteractionContext):
    button = Button(style=ButtonStyles.PRIMARY, label="Hello!", custom_id=f"hello{ctx.id}")
    await ctx.send("Hello, World!", components=[ActionRow(button)])
    
    
@interaction.context_menu(name="say", menu_type=3)
async def say_menu(ctx: InteractionContext):
    await ctx.send(f"You said: {ctx.target.content}")
    

@interaction.component_callback("hello")
async def hello_callback(ctx: InteractionContext):
    await ctx.send("Hello again!", ephemeral=True)

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("cert.pem", "privkey.pem")
server.run(host='0.0.0.0', port=1337, ssl_context=ssl_context)

```
