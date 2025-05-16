from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands, Attachment, Colour
from tortoise.exceptions import IntegrityError

from business_logic import parse_html

from dotenv import load_dotenv
import os

from db import Squadron, StatusEnum, init_db, SquadronSettings, BattleLog, SquadronPlayer, PlayerBattleLog

# Load .env file into environment variables
load_dotenv()
api_key = os.getenv("API_KEY")

class Client(commands.Bot):
    async def on_ready(self):
        print(f"Logged on as {self.user}!")
        await init_db()
        try:
            guild = discord.Object(id=1372919660126671011)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f"Error syncing commands: {e}")


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=1372919660126671011)


@client.tree.command(name="register_squadron", description="Register a new squadron", guild=GUILD_ID)
@app_commands.describe(
    name="Squadron name (max 10 characters)",
)
async def register_squadron(interaction: discord.Interaction, name: str):
    if len(name) > 10:
        await interaction.response.send_message("Squadron name too long (max 10 characters).", ephemeral=True)
        return
    try:
        squadron = await Squadron.create(
            discord_id=interaction.guild_id,
            squadron_name=name,
            status=StatusEnum.ACTIVE
        )
        squadron_settings = await SquadronSettings.create(
            squadron=squadron,
            one_line_embed_enabled=False  # default value, or True if you want
        )
        await interaction.response.send_message(f"✅ Squadron '{name}' registered successfully!")
    except IntegrityError:
        await interaction.response.send_message(f"❌ Squadron already exists for this server.", ephemeral=True)


@client.tree.command(name="show_settings", description="Show squadron settings", guild=GUILD_ID)
async def show_settings(interaction: discord.Interaction):
    discord_id = interaction.guild_id  # Or however you track the squadron
    try:
        squadron = await Squadron.get(discord_id=discord_id)
        if squadron.status == "INACTIVE" or squadron is None:
            await interaction.response.send_message(f"Squadron doesn't exists")
            return
        settings = await SquadronSettings.get(squadron=squadron)
        squadron_settings = {
            "single_line_logs": settings.one_line_embed_enabled
        }
        await interaction.response.send_message(f"Current settings: \n"
                                                f"SINGLE_LINE_LOGS:  {squadron_settings.get('single_line_logs', '')}")
    except Exception as e:
        print("ERROR:", e)
        await interaction.response.send_message(
            f"Failed to fetch settings: Seems like you have not registered your squadron")


# @app_commands.describe(name="Single line log - Y/y or N/n")
@client.tree.command(name="settings_single_line_logs", description="Single line log - Y/y or N/n", guild=GUILD_ID)
async def set_single_line_log(interaction: discord.Interaction, response: str):
    discord_id = interaction.guild_id

    if response not in ["Y", "y", "N", "n"]:
        await interaction.response.send_message("Invalid response, respond as Y/y for Yes or N/n for No")
        return
    settings_flag = True if response in ["Y", "y"] else False
    try:
        squadron = await Squadron.get(discord_id=discord_id)
        if squadron.status == "INACTIVE" or squadron is None:
            await interaction.response.send_message(f"Squadron doesn't exists")
            return
        settings = await SquadronSettings.get(squadron=squadron)
        settings.one_line_embed_enabled = settings_flag
        await settings.save()
        await interaction.response.send_message(f"✅ SINGLE_LINES_LOGS set to {settings_flag}")
    except Exception as e:
        await interaction.response.send_message(f"❌ Error while modifying settings: {e}", ephemeral=True)


@client.tree.command(name="log_svs_battle", description="Upload the HTML replay file to log the battle", guild=GUILD_ID)
@app_commands.describe(file="Upload the HTML file exported from replay page")
async def log_svs_battle(interaction: discord.Interaction, file: Attachment, battle_verdict: str, enemy_squadron: str):
    discord_id = interaction.guild_id
    squadron = await Squadron.get(discord_id=discord_id)

    # Ensure it's a text file
    if not file.filename.endswith(".html") and not file.filename.endswith(".txt"):
        await interaction.response.send_message("Please upload a valid .html or .txt file.", ephemeral=True)
        return

    # Read file content as string
    content = await file.read()
    html_content = content.decode("utf-8")

    # Parse and respond
    parsed_result = parse_html(html_content)
    # await interaction.response.send_message(parsed_result)
    embed_color = Colour.green() if battle_verdict == "win" else Colour.red()
    embed_title = f"{'WIN' if battle_verdict == 'win' else 'LOST'} \t [{squadron.squadron_name} vs {enemy_squadron}]"

    squadron_settings = await SquadronSettings.get(squadron=squadron)

    if squadron_settings.one_line_embed_enabled:
        embed = discord.Embed(title=f"{embed_title}", description="", color=embed_color)
    else:
        embed = discord.Embed(title=f"{embed_title}", description=parsed_result.get("battle_map"), color=embed_color)
        embed.add_field(name="", value=parsed_result.get("description", ""), inline=False)
        embed.add_field(name="", value=parsed_result.get("time_stamp", ""))
        embed.add_field(name="Duration", value=parsed_result.get("match_duration", ""))
        embed.add_field(name="Session ID", value=parsed_result.get("session_id", ""), inline=False)

    if squadron.status == "INACTIVE" or squadron is None:
        await interaction.response.send_message(f"Squadron doesn't exists")
        return

    # try:
    battle_log = await BattleLog.create(
        squadron=squadron,
        map_name=parsed_result.get("", ""),
        battle_description=parsed_result.get("", ""),
        duration=parsed_result.get("match_duration", ""),
        session_id=parsed_result.get("session_id", ""),
        verdict='WIN' if battle_verdict == 'win' else 'LOST',
        timestamp=datetime.strptime(parsed_result.get("time_stamp", ""), "%d %b %Y - %H:%M")
    )

    for player in parsed_result.get("team_1", []):
        player_exist = await SquadronPlayer.get_or_none(player_id=player[0])

        if player_exist is None:
            new_player = await SquadronPlayer.create(
                squadron=squadron,
                player_id=player[0],
                player_name=player[1],
                status="ACTIVE"
            )
            await PlayerBattleLog.create(
                battle_log=battle_log,
                player=new_player
            )
        else:
            await PlayerBattleLog.create(
                battle_log=battle_log,
                player=player_exist
            )
    await interaction.response.send_message(embed=embed)
# except Exception as e:
#     await interaction.response.send_message(f"Error while logging battle details: {e}")


client.run(api_key)
