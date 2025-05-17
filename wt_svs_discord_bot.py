from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands, Attachment, Colour
from tortoise.exceptions import IntegrityError, DoesNotExist
from business_logic import parse_html
from dotenv import load_dotenv
import os

from db import Squadron, StatusEnum, init_db, SquadronSettings, BattleLog, SquadronPlayer, PlayerBattleLog

# Load environment variables
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
            print(f"[Sync Error] {e}")


intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=1372919660126671011)


@client.tree.command(name="register_squadron", description="Register a new squadron", guild=GUILD_ID)
@app_commands.describe(name="Squadron name (max 10 characters)")
async def register_squadron(interaction: discord.Interaction, name: str):
    if len(name) > 10:
        await interaction.response.send_message("❌ Squadron name too long (max 10 characters).", ephemeral=True)
        return
    try:
        existing = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if existing:
            await interaction.response.send_message("❌ A squadron is already registered for this server.",
                                                    ephemeral=True)
            return

        squadron = await Squadron.create(
            discord_id=interaction.guild_id,
            squadron_name=name,
            status=StatusEnum.ACTIVE
        )
        await SquadronSettings.create(squadron=squadron, one_line_embed_enabled=False)
        await interaction.response.send_message(f"✅ Squadron '{name}' registered successfully!")
    except IntegrityError:
        await interaction.response.send_message("❌ Squadron already exists.", ephemeral=True)
    except Exception as e:
        print("[Register Error]", e)
        await interaction.response.send_message("❌ An unexpected error occurred while registering the squadron.",
                                                ephemeral=True)


@client.tree.command(name="show_settings", description="Show squadron settings", guild=GUILD_ID)
async def show_settings(interaction: discord.Interaction):
    try:
        squadron = await Squadron.get(discord_id=interaction.guild_id)
        if not squadron or squadron.status == StatusEnum.INACTIVE:
            await interaction.response.send_message("❌ Squadron doesn't exist or is inactive.", ephemeral=True)
            return

        settings = await SquadronSettings.get(squadron=squadron)
        await interaction.response.send_message(
            f"Current settings:\nSINGLE_LINE_LOGS: {settings.one_line_embed_enabled}"
        )
    except DoesNotExist:
        await interaction.response.send_message("❌ Squadron not registered.", ephemeral=True)
    except Exception as e:
        print("[Show Settings Error]", e)
        await interaction.response.send_message("❌ Failed to fetch settings.", ephemeral=True)


@client.tree.command(name="settings_single_line_logs", description="Single line log - Y/y or N/n", guild=GUILD_ID)
async def set_single_line_log(interaction: discord.Interaction, response: str):
    if response not in ["Y", "y", "N", "n"]:
        await interaction.response.send_message("❌ Invalid response. Use Y/y for Yes or N/n for No.", ephemeral=True)
        return

    try:
        squadron = await Squadron.get(discord_id=interaction.guild_id)
        if not squadron or squadron.status == StatusEnum.INACTIVE:
            await interaction.response.send_message("❌ Squadron doesn't exist or is inactive.", ephemeral=True)
            return

        settings = await SquadronSettings.get(squadron=squadron)
        settings.one_line_embed_enabled = response.lower() == "y"
        await settings.save()
        await interaction.response.send_message(f"✅ SINGLE_LINE_LOGS set to {settings.one_line_embed_enabled}")
    except Exception as e:
        print("[Set Setting Error]", e)
        await interaction.response.send_message(f"❌ Failed to update settings|Error:{e}", ephemeral=True)


@client.tree.command(name="log_svs_battle", description="Upload the HTML replay file to log the battle", guild=GUILD_ID)
@app_commands.describe(file="Upload the HTML file exported from replay page")
async def log_svs_battle(interaction: discord.Interaction, file: Attachment, battle_verdict: str, enemy_squadron: str):
    if not file.filename.endswith(".html") and not file.filename.endswith(".txt"):
        await interaction.response.send_message("❌ Please upload a valid .html or .txt file.", ephemeral=True)
        return

    try:
        content = await file.read()
        html_content = content.decode("utf-8")
        parsed_result = parse_html(html_content)

        squadron = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if squadron is None or squadron.status == StatusEnum.INACTIVE:
            await interaction.response.send_message("❌ Squadron doesn't exist or is inactive.", ephemeral=True)
            return

        squadron_settings = await SquadronSettings.get(squadron=squadron)
        embed_color = Colour.green() if battle_verdict.lower() == "win" else Colour.red()
        embed_title = f"{'WIN' if battle_verdict.lower() == 'win' else 'LOST'} - [{squadron.squadron_name} vs {enemy_squadron}]"

        embed = discord.Embed(title=embed_title, color=embed_color)
        if not squadron_settings.one_line_embed_enabled:
            embed.description = parsed_result.get("battle_map", "")
            embed.add_field(name="", value=parsed_result.get("description", ""), inline=False)
            embed.add_field(name="", value=parsed_result.get("time_stamp", ""))
            embed.add_field(name="Duration", value=parsed_result.get("match_duration", ""))
            embed.add_field(name="Session ID", value=parsed_result.get("session_id", ""), inline=False)

        battle_log = await BattleLog.create(
            squadron=squadron,
            map_name=parsed_result.get("battle_map", ""),
            battle_description=parsed_result.get("description", ""),
            duration=parsed_result.get("match_duration", ""),
            session_id=parsed_result.get("session_id", ""),
            verdict="WIN" if battle_verdict.lower() == "win" else "LOST",
            timestamp=datetime.strptime(parsed_result.get("time_stamp", ""), "%d %b %Y - %H:%M")
        )

        for player_id, player_name, player_url in parsed_result.get("team_1", []):
            player = await SquadronPlayer.get_or_none(player_id=player_id)
            if not player:
                player = await SquadronPlayer.create(
                    squadron=squadron,
                    player_id=player_id,
                    player_name=player_name,
                    status="ACTIVE"
                )
            await PlayerBattleLog.create(battle_log=battle_log, player=player)

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print("[Log Battle Error]", e)
        await interaction.response.send_message(f"❌ Error while logging battle|Error:{e}",
                                                ephemeral=True)


client.run(api_key)
