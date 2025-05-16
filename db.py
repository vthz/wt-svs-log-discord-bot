import asyncio
from enum import Enum

from tortoise import Tortoise, fields, models
import os
from dotenv import load_dotenv

load_dotenv()


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
    session_id = fields.CharField(max_length=50)
    verdict = fields.CharField(max_length=10)
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


async def run():
    await init_db()
    print("✅ Database schema generated!")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run())
