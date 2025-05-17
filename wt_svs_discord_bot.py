from datetime import datetime, timedelta, timezone
from typing import Optional

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


@client.tree.command(name="help", description="List all available bot commands", guild=GUILD_ID)
async def show_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📘 Bot Commands Help",
        description="Here’s a list of all available commands and what they do:",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="/register_squadron [name]",
        value="Registers a new squadron for this Discord server.\n🛑 Max 10 characters.\n✅ One squadron per server.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/rename_squadron",
        value="Rename your registered squadron (max 10 characters).",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/show_settings",
        value="Displays the current settings for this squadron.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/settings_single_line_logs [Y/N]",
        value="Sets whether battle logs are shown in a single-line format.\n✔️ Use 'Y' or 'N'.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/log_svs_battle [file] [battle_verdict] [enemy_squadron]",
        value=(
            "Logs a battle using an exported HTML file.\n"
            "📎 File: Upload the replay HTML or TXT file\n"
            "⚔️ Verdict: `win` or `lost`\n"
            "🏴 Enemy Squadron: name of the enemy squadron"
        ),
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/help",
        value="Shows this help message.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/show_battle_log_count [number]",
        value="Show the most recent [number] of battle logs.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.add_field(
        name="/show_todays_battle_log",
        value="Show today's battle logs for the squadron.",
        inline=False
    )
    embed.add_field(name="\u200b", value="", inline=False)

    embed.set_footer(text="Use slash commands to interact with the bot.")

    await interaction.response.send_message(embed=embed, ephemeral=True)



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

@client.tree.command(name="rename_squadron", description="Rename the registered squadron", guild=GUILD_ID)
@app_commands.describe(new_name="New squadron name (max 10 characters)")
async def rename_squadron(interaction: discord.Interaction, new_name: str):
    if len(new_name) > 10:
        await interaction.response.send_message("❌ Squadron name too long (max 10 characters).", ephemeral=True)
        return

    try:
        squadron = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if not squadron:
            await interaction.response.send_message("❌ No squadron is registered for this server.", ephemeral=True)
            return

        old_name = squadron.squadron_name
        squadron.squadron_name = new_name
        await squadron.save()

        await interaction.response.send_message(
            f"✅ Squadron renamed from '{old_name}' to '{new_name}' successfully!"
        )
    except Exception as e:
        print("[Rename Error]", e)
        await interaction.response.send_message("❌ An unexpected error occurred while renaming the squadron.",
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
            timestamp=datetime.strptime(parsed_result.get("time_stamp", ""), "%d %b %Y - %H:%M"),
            enemy_squadron=enemy_squadron,
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


from discord import Embed

@client.tree.command(
    name="show_battle_log_count",
    description="Show recent battle logs for this squadron",
    guild=GUILD_ID
)
@app_commands.describe(count="Number of recent battle logs to show (default: 5)")
async def show_battle_log_count(interaction: discord.Interaction, count: Optional[int] = 5):
    try:
        if count is not None and count <= 0:
            await interaction.response.send_message("❌ Count must be a positive number.", ephemeral=True)
            return

        squadron = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if not squadron:
            await interaction.response.send_message("❌ No squadron is registered for this server.", ephemeral=True)
            return

        logs = await BattleLog.filter(squadron=squadron).order_by('-timestamp')
        total_logs = len(logs)

        if total_logs == 0:
            await interaction.response.send_message("📭 No battle logs found.")
            return

        selected_logs = logs[:count]

        embed = Embed(
            title=f"📚 Showing last {len(selected_logs)} of {total_logs} battle logs",
            color=0x2F3136  # Default dark embed color
        )

        for i, log in enumerate(selected_logs, 1):
            # Choose emoji color based on verdict
            verdict_emoji = "🟩" if log.verdict.upper() == "WIN" else "🟥"
            # Build field value string
            field_value = (
                f"{log.map_name}\n"
                f"{log.timestamp.strftime('%b %d, %Y %H:%M UTC')}"
            )
            embed.add_field(name=f"Battle {i} | vs {log.enemy_squadron} | {verdict_emoji}", value=field_value, inline=False)

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print("[Show Battle Log Count Error]", e)
        await interaction.response.send_message("❌ An error occurred while retrieving battle logs.", ephemeral=True)


@client.tree.command(name="show_todays_battle_log", description="Show today’s battle logs for this squadron", guild=GUILD_ID)
async def show_todays_battle_log(interaction: discord.Interaction):
    try:
        squadron = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if not squadron:
            await interaction.response.send_message("❌ No squadron is registered for this server.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        logs = await BattleLog.filter(squadron=squadron, timestamp__gte=start_of_day).order_by('-timestamp')

        if not logs:
            await interaction.response.send_message("📭 No battle logs found for today.")
            return

        log_messages = [
            f"🧾 **{log.map_name}** | {log.battle_description} | {log.verdict} | {log.duration}"
            for log in logs[:10]
        ]
        message = "\n".join(log_messages)
        await interaction.response.send_message(f"📅 Today’s Battle Logs:\n\n{message}")
    except Exception as e:
        print("[Show Today's Battle Log Error]", e)
        await interaction.response.send_message("❌ An error occurred while retrieving today's battle logs.", ephemeral=True)


from typing import Optional

from typing import Optional
from datetime import datetime, timedelta, timezone

@client.tree.command(
    name="most_battle_contributor",
    description="Show a ranked list of players with the most battles in this squadron",
    guild=GUILD_ID
)
@app_commands.describe(
    top_n="Number of top contributors to display (default is 10)",
    days="Filter battles from the last X days (optional)"
)
async def most_battle_contributor(
    interaction: discord.Interaction,
    top_n: Optional[int] = 10,
    days: Optional[int] = None
):
    try:
        squadron = await Squadron.get_or_none(discord_id=interaction.guild_id)
        if not squadron:
            await interaction.response.send_message("❌ No squadron registered for this server.", ephemeral=True)
            return

        players = await SquadronPlayer.filter(squadron=squadron)
        if not players:
            await interaction.response.send_message("❌ No players found in this squadron.", ephemeral=True)
            return

        # Optional date filter
        recent_cutoff = None
        if days is not None and days > 0:
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        player_battle_counts = []

        for player in players:
            if recent_cutoff:
                count = await PlayerBattleLog.filter(
                    player=player,
                    battle_log__timestamp__gte=recent_cutoff
                ).count()
            else:
                count = await PlayerBattleLog.filter(player=player).count()

            if count > 0:
                player_battle_counts.append((player.player_name, count))

        if not player_battle_counts:
            await interaction.response.send_message("📭 No battle logs found for the specified period.", ephemeral=True)
            return

        sorted_players = sorted(player_battle_counts, key=lambda x: x[1], reverse=True)
        top_players = sorted_players[:top_n]

        leaderboard = "\n".join([
            f"🏅 **#{i + 1}** — 🧑 **{name}** | 🎯 Battles: `{count}`"
            for i, (name, count) in enumerate(top_players)
        ])

        title = f"🏆 Top {len(top_players)} Battle Contributors"
        if days:
            title += f" (Last {days} days)"

        embed = discord.Embed(
            title=title,
            description=leaderboard,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Based on player participation in recorded battles")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        print("[Most Battle Contributor Error]", e)
        await interaction.response.send_message("❌ An error occurred while fetching battle contributor data.", ephemeral=True)

client.run(api_key)
