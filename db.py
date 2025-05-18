import asyncio
from enum import Enum

from tortoise import Tortoise, fields, models
import os
from dotenv import load_dotenv

load_dotenv()

# Dynamically get the user's Desktop path
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
db_folder = os.path.join(desktop_path, "wt-svs-discord-bot")
os.makedirs(db_folder, exist_ok=True)  # Ensure the folder exists

DB_FILE = os.path.join(db_folder, "wt_discord_bot_db.sqlite3")


class StatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Squadron(models.Model):
    squadron_id = fields.IntField(pk=True)
    discord_id = fields.BigIntField(unique=True)
    status = fields.CharEnumField(StatusEnum, default=StatusEnum.ACTIVE)
    squadron_name = fields.CharField(max_length=10)

    class Meta:
        table = "squadron"


class SquadronSettings(models.Model):
    id = fields.IntField(pk=True)
    squadron = fields.ForeignKeyField("models.Squadron", related_name="settings")
    one_line_embed_enabled = fields.BooleanField(default=False)

    class Meta:
        table = "squadron_settings"


class BattleLog(models.Model):
    id = fields.IntField(pk=True)
    squadron = fields.ForeignKeyField("models.Squadron", related_name="battles")
    map_name = fields.CharField(max_length=100)
    battle_description = fields.CharField(max_length=100)
    duration = fields.CharField(max_length=20)
    session_id = fields.CharField(max_length=50, unique=True)
    verdict = fields.CharField(max_length=10)
    enemy_squadron = fields.CharField(max_length=10)
    timestamp = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "battle_log"


class SquadronPlayer(models.Model):
    id = fields.IntField(pk=True)
    squadron = fields.ForeignKeyField("models.Squadron", related_name="players")
    player_id = fields.BigIntField(unique=True)
    player_name = fields.CharField(max_length=50)
    status = fields.CharEnumField(StatusEnum, default=StatusEnum.ACTIVE)

    class Meta:
        table = "squadron_players"


class PlayerBattleLog(models.Model):
    id = fields.IntField(pk=True)
    battle_log = fields.ForeignKeyField("models.BattleLog", related_name="player_battle_log")
    player = fields.ForeignKeyField("models.SquadronPlayer", related_name="squadron_players")

    class Meta:
        table = "player_battle_log"


async def init_db():
    port = int(os.getenv("DB_PORT").strip())

    await Tortoise.init(
        db_url=(
            f"postgres://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{port}/{os.getenv('DB_NAME')}"
        ),
        modules={"models": ["db"]}
    )
    await Tortoise.generate_schemas()


# async def run():
#     await init_db()
#     print("✅ Database schema generated!")
#     await Tortoise.close_connections()

async def run_sqlite_db():
    # Step 1: Delete existing DB file if it exists
    # if os.path.exists(DB_FILE):
    #     os.remove(DB_FILE)
    #     print("🗑️ Old database file deleted.")

    # Step 2: Initialize Tortoise ORM with SQLite
    await Tortoise.init(
        db_url=f"sqlite://{DB_FILE}",
        modules={"models": ["db"]},  # replace "db" with the actual module name of your models
    )

    # Step 3: Generate schema (tables)
    await Tortoise.generate_schemas()
    print("✅ New SQLite database created.")

    # Step 4: Close connections
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_sqlite_db())
