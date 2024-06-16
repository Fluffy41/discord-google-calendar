import discord
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

tree = discord.app_commands.CommandTree(client)

"--> Bot says its own name"
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=1041717631910158447))
    print(f'We have logged in as {client.user}')
    
# make the slash command
@tree.command(
    name="test",
    description="Test command",
    guild=discord.Object(id=1041717631910158447)
)
async def test_command(interaction):
    await interaction.response.send_message("Hello, world!")
    
client.run(os.getenv('TOKEN'))